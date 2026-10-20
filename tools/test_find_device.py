import hashlib
import ipaddress
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import find_device
from find_device import build_admin_script, load_profile, normalize_mac, parse_scan, save_profile, validate_binding, verify_binary


MAC = ":".join(("02", "00", "00", "00", "00", "01"))
GATEWAY_MAC = ":".join(("02", "00", "00", "00", "00", "02"))


def observation():
    return {"interface": "en0", "network": "192.0.2.0/24", "address": "192.0.2.10",
            "netmask": str(ipaddress.ip_network("192.0.2.0/24").netmask), "gateway": "192.0.2.1",
            "gateway_mac": GATEWAY_MAC, "gateway_raw_mac": GATEWAY_MAC}


def binding():
    return {"approved": True, "interface": "en0", "network": "192.0.2.0/24",
            "gateway": "192.0.2.1", "gateway_mac": GATEWAY_MAC}


def scan_xml(entries=(), exit_status="success"):
    hosts = "".join(
        f'<host><status state="up" reason="arp-response"/><address addr="{address}" addrtype="ipv4"/>'
        f'<address addr="{mac}" addrtype="mac"/></host>' for address, mac in entries
    )
    return f'<?xml version="1.0"?><!DOCTYPE nmaprun><nmaprun scanner="nmap">{hosts}<runstats><finished exit="{exit_status}"/></runstats></nmaprun>'


class FindDeviceTest(unittest.TestCase):
    def test_mac_normalization_and_invalid_identifiers(self):
        self.assertEqual(normalize_mac(MAC.upper().replace(":", "-")), MAC)
        self.assertEqual(normalize_mac(":".join(("2", "0", "0", "0", "0", "1"))), MAC)
        for invalid in ("not a MAC", ":".join(["ff"] * 6), ":".join(["00"] * 6), ":".join(("01", "00", "00", "00", "00", "01"))):
            with self.assertRaises(ValueError):
                normalize_mac(invalid)

    def test_binding_rejects_network_interface_gateway_or_mac_changes(self):
        self.assertEqual(str(validate_binding(binding(), observation())), "192.0.2.0/24")
        for key, value in (("network", "198.51.100.0/24"), ("interface", "en1"),
                           ("gateway", "192.0.2.2"), ("gateway_mac", MAC)):
            changed = observation()
            changed[key] = value
            with self.assertRaises(ValueError):
                validate_binding(binding(), changed)
        denied = binding()
        denied["approved"] = False
        with self.assertRaises(ValueError):
            validate_binding(denied, observation())

    def test_scan_matches_mac_deduplicates_and_preserves_ambiguity(self):
        xml = scan_xml((("192.0.2.20", MAC.upper()), ("192.0.2.20", MAC), ("192.0.2.21", MAC), ("192.0.2.1", GATEWAY_MAC)))
        rows, addresses = parse_scan(xml, "192.0.2.0/24", MAC)
        self.assertEqual(len(rows), 3)
        self.assertEqual(addresses, ["192.0.2.20", "192.0.2.21"])
        self.assertEqual(parse_scan(scan_xml(), "192.0.2.0/24", MAC), ([], []))

    def test_failed_malformed_or_out_of_scope_scan_is_rejected(self):
        for xml in (scan_xml(exit_status="error"), "not XML", scan_xml((("198.51.100.1", MAC),)),
                    '<!DOCTYPE nmaprun [<!ENTITY x "unsafe">]><nmaprun/>',
                    scan_xml().replace("<runstats>", '<scaninfo type="connect"/><runstats>')):
            with self.assertRaises(ValueError):
                parse_scan(xml, "192.0.2.0/24", MAC)

    def test_binary_pin_rejects_changed_file_or_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "nmap"
            file.write_bytes(b"synthetic executable")
            file.chmod(0o700)
            expected = hashlib.sha256(file.read_bytes()).hexdigest()
            verify_binary(file, expected)
            with self.assertRaises(ValueError):
                verify_binary(file, "incorrect pin")
            link = Path(directory) / "alias"
            link.symlink_to(file)
            with self.assertRaises(ValueError):
                verify_binary(link, expected)

    def test_private_profile_rejects_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = root / "backups/device-profiles"
            (root / "backups").mkdir(mode=0o700)
            profiles.mkdir(mode=0o700)
            for alias in ("../escape", "not safe", "/absolute"):
                with self.assertRaises(ValueError):
                    load_profile(root, alias)
            file = profiles / "photo-frame.json"
            file.symlink_to(root / "elsewhere")
            with self.assertRaises(ValueError):
                load_profile(root, "photo-frame")

    def test_profile_loads_only_owner_private_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "backups").mkdir(mode=0o700)
            profiles = root / "backups/device-profiles"
            profiles.mkdir(mode=0o700)
            path = profiles / "photo-frame.json"
            path.write_text(json.dumps({"mac": MAC, "discovery": binding()}))
            path.chmod(0o600)
            loaded, profile, original = load_profile(root, "photo-frame")
            self.assertEqual(loaded, path)
            self.assertEqual(profile["mac"], MAC)
            self.assertEqual(original, path.read_bytes())
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                load_profile(root, "photo-frame")

    def test_preflight_does_not_elevate_scan_or_write_profile(self):
        profile = {"mac": MAC, "discovery": {**binding(), "nmap_path": "/opt/example/nmap", "nmap_sha256": "a" * 64}}
        with patch.object(find_device.platform, "system", return_value="Darwin"), \
                patch.object(find_device.os, "geteuid", return_value=501), \
                patch.object(find_device, "load_profile", return_value=(Path("unused"), profile, b"")), \
                patch.object(find_device, "current_network", return_value=observation()), \
                patch.object(find_device, "verify_binary"), \
                patch.object(find_device.subprocess, "run") as run, \
                patch.object(find_device, "save_profile") as save, \
                patch("sys.argv", ["find_device", "photo-frame", "--check", "--json"]), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(find_device.main(), 0)
            self.assertFalse(json.loads(output.getvalue())["scan_performed"])
            run.assert_not_called()
            save.assert_not_called()

    def test_profile_checkpoint_preserves_a_concurrent_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            original = b'{}'
            path.write_bytes(original)
            save_profile(path, {"status": "example"}, original)
            self.assertEqual(json.loads(path.read_text()), {"status": "example"})
            with self.assertRaises(ValueError):
                save_profile(path, {"status": "overwrite"}, original)
            self.assertEqual(json.loads(path.read_text()), {"status": "example"})

    def test_elevated_command_is_bounded_arp_and_rechecks_after_prompt(self):
        script = build_admin_script(observation(), "/opt/example/nmap", "a" * 64)
        for required in ("-sn", "-PR", "--send-eth", "--host-timeout", "with administrator privileges", "ipconfig", "openssl"):
            self.assertIn(required, script)
        for forbidden in ("--script", "-sV", "-O ", " -p ", "adb", "password"):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
