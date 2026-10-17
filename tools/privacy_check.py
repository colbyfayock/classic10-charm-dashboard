#!/usr/bin/env python3
"""Inspect Git blobs without echoing potentially sensitive matching text."""

import argparse
import ipaddress
from pathlib import PurePosixPath
import re
import subprocess
import sys


PRIVATE_DIRS = {"backups", "diagnostics", "frames", "private", "logs"}
PRIVATE_SUFFIXES = (".img", ".img.gz", ".bin", ".dump", ".raw", ".apk", ".apks", ".aab", ".ab", ".keystore", ".jks", ".p12", ".pem", ".key")
DOCUMENTATION_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32",
))


def inspect_blob(path, data):
    """Return rule names only; raw matches must never appear in diagnostics."""
    findings = set()
    name = PurePosixPath(path).name.lower()
    if (PRIVATE_DIRS.intersection(PurePosixPath(path.lower()).parts)
            or name.endswith(PRIVATE_SUFFIXES)
            or name in {"adbkey", "adbkey.pub", "credentials.json", "secrets.json"}
            or (name.startswith(".env") and name != ".env.example")):
        findings.add("private artifact path")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return sorted(findings | {"binary content requires review"})
    if b"\0" in data:
        findings.add("binary content requires review")

    # This exact, non-unique software version is not a device address.
    address_text = text
    if path == "docs/device.md":
        address_text = address_text.replace("VPhoto " + ".".join(("2", "1", "3", "34")), "VPhoto VERSION")
    candidates = re.findall(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", address_text)
    candidates += re.findall(r"(?<![\w:])(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F:.%]*(?![\w:])", address_text)
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        safe = address.is_loopback or any(
            address.version == network.version and address in network
            for network in DOCUMENTATION_NETWORKS
        )
        if not safe:
            findings.add("network address")
    if re.search(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b", text, re.I):
        findings.add("MAC address")
    if re.search(r"\b(?:SN|serial(?:[ _-]?number)?)\s*[:=]\s*[\"']?[a-z0-9-]{8,}", text, re.I):
        findings.add("device serial")
    if re.search(r"(?:whole[ -]?(?:disk|emmc)|emmc[ -]?full)[^\n]{0,80}\b[0-9a-f]{64}\b", text, re.I):
        findings.add("whole-disk hash")
    assignments = re.finditer(
        r"\b(?:api[_-]?key|password|passwd|access[_-]?token|secret|wifi[_-]?(?:ssid|password)|ssid)"
        r"[\"']?\s*[:=]\s*[\"']?([^\s\"',;}]+)", text, re.I,
    )
    placeholders = {"YOUR_API_KEY", "YOUR_PASSWORD", "YOUR_TOKEN", "YOUR_SSID", "YOUR_SECRET"}
    for assignment in assignments:
        value = assignment.group(1)
        if value not in placeholders and not value.startswith(("${", "<")):
            findings.add("sensitive assignment")
    return sorted(findings)


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Scan only staged additions and modifications")
    args = parser.parse_args()
    paths = (git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
             if args.staged else git("ls-files", "-z"))
    failed = False
    for raw_path in paths.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8")
        # Read the actual index blob, never the potentially different working copy.
        for finding in inspect_blob(path, git("show", ":" + path)):
            print(f"{path}: {finding}")
            failed = True
    if not failed:
        print("Privacy scan passed.")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
