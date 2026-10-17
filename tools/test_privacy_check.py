import unittest
from pathlib import Path
import subprocess
import sys
import tempfile

from privacy_check import inspect_blob


class PrivacyCheckTest(unittest.TestCase):
    def test_scans_staged_blob_instead_of_clean_working_copy(self):
        scanner = Path(__file__).with_name("privacy_check.py").resolve()
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            target = Path(directory) / "note.md"
            target.write_text("10." + "23.45.67")
            subprocess.run(["git", "-C", directory, "add", "note.md"], check=True)
            target.write_text("FRAME_ADDRESS")
            result = subprocess.run(
                [sys.executable, str(scanner), "--staged"],
                cwd=directory, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("network address", result.stdout)
            self.assertNotIn("10." + "23.45.67", result.stdout)

    def test_allows_examples_and_versions(self):
        text = b"127.0.0.1 ::1 192.0.2.1 2001:db8::1 FRAME_ADDRESS 4.4.2 1.2.3.4.5"
        self.assertEqual(inspect_blob("README.md", text), [])

    def test_blocks_real_ipv4_without_disclosing_it(self):
        value = "10." + "23.45.67"
        findings = inspect_blob("docs/device.md", value.encode())
        self.assertIn("network address", findings)
        self.assertNotIn(value, str(findings))

    def test_blocks_ipv6(self):
        value = ":".join(("fd12", "3456", "789a", "", "1"))
        self.assertIn("network address", inspect_blob("note.md", value.encode()))

    def test_allows_only_documented_vphoto_version_in_device_record(self):
        version = ".".join(("2", "1", "3", "34"))
        self.assertEqual(inspect_blob("docs/device.md", ("VPhoto " + version).encode()), [])
        self.assertIn("network address", inspect_blob("note.md", version.encode()))

    def test_blocks_serial_and_mac(self):
        serial = "SN:" + "EXAMPLEUNIT123456"
        mac = ":".join(["12", "34", "56", "78", "9a", "bc"])
        self.assertIn("device serial", inspect_blob("note.md", serial.encode()))
        self.assertIn("MAC address", inspect_blob("note.md", mac.encode()))

    def test_blocks_private_paths_and_artifacts(self):
        for path in ("backups/capture.txt", "frame.apk", "disk.img.gz", ".env", "adbkey"):
            self.assertIn("private artifact path", inspect_blob(path, b"example"))

    def test_blocks_credential_assignments_without_echoing_values(self):
        value = "not-a-real-" + "credential-12345"
        for name in ("API_KEY", "password", "wifi_ssid", "access_token"):
            text = name + ' = "' + value + '"'
            findings = inspect_blob("settings.txt", text.encode())
            self.assertIn("sensitive assignment", findings)
            self.assertNotIn(value, str(findings))

    def test_allows_explicit_credential_placeholders(self):
        self.assertEqual(inspect_blob("example.txt", b'API_KEY="YOUR_API_KEY"'), [])

    def test_blocks_binary_and_whole_disk_hash(self):
        self.assertIn("binary content requires review", inspect_blob("unknown.dat", b"a\x00b"))
        self.assertIn("whole-disk hash", inspect_blob("note.md", b"whole-disk SHA256: " + b"a" * 64))


if __name__ == "__main__":
    unittest.main()
