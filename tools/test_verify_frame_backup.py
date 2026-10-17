import gzip
import hashlib
from pathlib import Path
import tempfile
import unittest

from verify_frame_backup import hash_ranges


class VerifyFrameBackupTest(unittest.TestCase):
    def test_hashes_overlapping_ranges_across_read_boundaries(self):
        data = bytes(range(256)) * 1000
        ranges = {"header": (0, 1024), "crossing": (65000, 2000), "overlap": (65500, 1000)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.gz"
            path.write_bytes(gzip.compress(data))
            result = hash_ranges(path, ranges, len(data), hashlib.sha256(data).hexdigest())
        for name, (start, length) in ranges.items():
            self.assertEqual(result[name], hashlib.sha256(data[start:start + length]).hexdigest())

    def test_rejects_truncation_wrong_digest_and_out_of_bounds_range(self):
        data = b"example"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.gz"
            path.write_bytes(gzip.compress(data))
            for ranges, length, digest in (
                ({"short": (0, 1)}, len(data) + 1, hashlib.sha256(data).hexdigest()),
                ({"short": (0, 1)}, len(data), "incorrect digest"),
                ({"outside": (0, 100)}, len(data), hashlib.sha256(data).hexdigest()),
            ):
                with self.assertRaises(ValueError):
                    hash_ranges(path, ranges, length, digest)


if __name__ == "__main__":
    unittest.main()
