import hashlib
import io
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from build_navigation_helper import extract_verified, verify_archive


class NavigationBuildTest(unittest.TestCase):
    def archive(self, name="root/nested/file", content=b"example", mode=0o100644):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            archive.writestr(info, content)
        return memory.getvalue()

    def test_published_size_and_both_hash_pins_are_enforced(self):
        data = b"synthetic archive"
        pin = {"size": len(data), "sha1": hashlib.sha1(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest()}
        verify_archive(data, pin)
        for field in ("size", "sha1", "sha256"):
            wrong = dict(pin)
            wrong[field] = 0 if field == "size" else "incorrect pin"
            with self.assertRaises(ValueError):
                verify_archive(data, wrong)

    def test_extraction_checks_existing_files_without_overwriting(self):
        data = self.archive()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            extract_verified(data, "root", target)
            extract_verified(data, "root", target)
            file = target / "nested/file"
            self.assertEqual(file.read_bytes(), b"example")
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
            file.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                extract_verified(data, "root", target)
            self.assertEqual(file.read_bytes(), b"changed")

    def test_extraction_rejects_traversal_foreign_roots_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            for data in (
                self.archive("root/../escape"),
                self.archive("/absolute/file"),
                self.archive("other/file"),
                self.archive("root/link", b"outside", 0o120777),
            ):
                with self.assertRaises(ValueError):
                    extract_verified(data, "root", Path(directory))


if __name__ == "__main__":
    unittest.main()
