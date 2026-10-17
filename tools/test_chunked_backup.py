import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from chunked_backup import capture_lock, make_plan, run_session


class ChunkedBackupTest(unittest.TestCase):
    def test_lock_prevents_simultaneous_capture_and_releases_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            with capture_lock(Path(directory)):
                with self.assertRaises(ValueError):
                    with capture_lock(Path(directory)):
                        self.fail("Second capture acquired the lock")
            with capture_lock(Path(directory)):
                pass

    def small_plan(self):
        return [
            {"area": "emmc", "offset": n * 65536, "size": 65536, "file": f"emmc-{n:06d}.img.gz"}
            for n in range(2)
        ]

    def reader(self, calls, fail=None):
        def capture(item, path):
            calls.append(item["file"])
            if item["file"] == fail:
                path.with_name(path.name + ".partial").write_bytes(b"unfinished")
                raise KeyboardInterrupt()
            data = bytes([item["offset"] // 65536]) * item["size"]
            path.write_bytes(gzip.compress(data))
            return hashlib.sha256(data).hexdigest()
        return capture

    def test_plan_covers_all_areas_exactly_with_bounded_chunks(self):
        plan = make_plan(64 * 1048576)
        for area, size in (("boot0", 4194304), ("boot1", 4194304), ("emmc", 15758000128)):
            offset = 0
            for item in (item for item in plan if item["area"] == area):
                self.assertEqual(item["offset"], offset)
                self.assertLessEqual(item["size"], 64 * 1048576)
                offset += item["size"]
            self.assertEqual(offset, size)

    def test_resume_preserves_verified_chunks_and_retries_interrupted_one(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            calls = []
            with self.assertRaises(KeyboardInterrupt):
                run_session(folder, "synthetic identity", self.small_plan(), self.reader(calls, "emmc-000001.img.gz"))
            checkpoint = json.loads((folder / "checkpoint.json").read_text())
            self.assertEqual(len(checkpoint["completed"]), 1)
            first = (folder / "emmc-000000.img.gz").read_bytes()
            calls = []
            run_session(folder, "synthetic identity", self.small_plan(), self.reader(calls))
            self.assertEqual(calls, ["emmc-000001.img.gz"])
            self.assertEqual((folder / "emmc-000000.img.gz").read_bytes(), first)
            self.assertTrue(list((folder / "interrupted").iterdir()))

    def test_resume_rejects_changed_identity_or_plan_before_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            run_session(folder, "first identity", self.small_plan(), self.reader([]))
            for identity, plan in (("other identity", self.small_plan()), ("first identity", self.small_plan()[:1])):
                with self.assertRaises(ValueError):
                    run_session(folder, identity, plan, self.reader([]))

    def test_corrupt_completed_chunk_stops_resume_instead_of_skipping_it(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            run_session(folder, "synthetic identity", self.small_plan(), self.reader([]))
            (folder / "emmc-000000.img.gz").write_bytes(b"corrupt")
            with self.assertRaises((ValueError, OSError, EOFError)):
                run_session(folder, "synthetic identity", self.small_plan(), self.reader([]))

    def test_orphan_completed_file_is_preserved_but_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "emmc-000000.img.gz").write_bytes(b"orphan")
            calls = []
            run_session(folder, "synthetic identity", self.small_plan(), self.reader(calls))
            self.assertEqual(len(calls), 2)
            self.assertTrue(list((folder / "interrupted").iterdir()))


if __name__ == "__main__":
    unittest.main()
