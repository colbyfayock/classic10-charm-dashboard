#!/usr/bin/env python3
"""Compare a private live capture with fresh reads of stable device ranges."""

import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shlex

from backup_frame import AREAS, adb_query, assert_identity, device_hash, verify_gzip


# Offsets describe only the exact firmware checked by assert_identity.
SAMPLES = {
    "disk_header": ("mmcblk0", 0, 65536, 0),
    "bootloader": ("mmcblk0p2", 0, 67108864, 73728 * 512),
    "env": ("mmcblk0p5", 0, 16777216, 204800 * 512),
    "boot": ("mmcblk0p6", 0, 16777216, 237568 * 512),
    "recovery": ("mmcblk0p9", 0, 33554432, 1875968 * 512),
    "system_first": ("mmcblk0p7", 0, 33554432, 270336 * 512),
    "system_middle": ("mmcblk0p7", 134217728, 33554432, 270336 * 512 + 134217728),
}


def hash_ranges(path, ranges, expected_size, expected_digest):
    """Re-read the whole gzip once while hashing bounded overlapping ranges."""
    for start, length in ranges.values():
        if start < 0 or length <= 0 or start + length > expected_size:
            raise ValueError("Sample outside expected image bounds")
    digests = {name: hashlib.sha256() for name in ranges}
    counts = {name: 0 for name in ranges}
    entire = hashlib.sha256()
    offset = 0
    with gzip.open(path, "rb") as source:
        while True:
            data = source.read(65536)
            if not data:
                break
            if data == bytes([204]) * 65536:
                raise ValueError("Suspicious uniform filler block")
            entire.update(data)
            for name, (start, length) in ranges.items():
                left = max(offset, start)
                right = min(offset + len(data), start + length)
                if right > left:
                    sample = data[left - offset:right - offset]
                    digests[name].update(sample)
                    counts[name] += len(sample)
            offset += len(data)
            if offset > expected_size:
                raise ValueError("Image exceeds expected size")
    if offset != expected_size or entire.hexdigest() != expected_digest:
        raise ValueError("Whole-image readback mismatch")
    if any(counts[name] != length for name, (_, length) in ranges.items()):
        raise ValueError("Incomplete sample range")
    return {name: digest.hexdigest() for name, digest in digests.items()}


def read_manifest(folder, area):
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Invalid backup session directory")
    manifest_path = folder / "manifest.json"
    image_path = folder / (area + ".img.gz")
    if manifest_path.is_symlink() or image_path.is_symlink():
        raise ValueError("Refusing symlinked backup files")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("area") != area or manifest.get("raw_bytes") != AREAS[area][1]:
        raise ValueError("Unexpected capture manifest")
    if not manifest.get("gzip_readback_verified") or not re.fullmatch(r"[0-9a-f]{64}", manifest.get("sha256", "")):
        raise ValueError("Missing successful capture metadata")
    return manifest, image_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="127.0.0.1:15555")
    parser.add_argument("--emmc-session", default="emmc-initial")
    parser.add_argument("--boot0-session", default="boot0-initial")
    parser.add_argument("--boot1-session", default="boot1-initial")
    args = parser.parse_args()
    names = {area: getattr(args, area + "_session") for area in AREAS}
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in names.values()):
        parser.error("Session names must be simple directory names")
    base = Path(__file__).resolve().parents[1] / "backups"
    if base.is_symlink():
        raise ValueError("Refusing symlinked backup parent")
    manifests = {area: read_manifest(base / session, area) for area, session in names.items()}
    assert_identity(args.transport)
    # Compare every partition involved in sample hashing against this unit's map.
    expected_partitions = {2: (73728, 131072), 5: (204800, 32768), 6: (237568, 32768), 7: (270336, 1572864), 9: (1875968, 65536)}
    for partition, (start, size) in expected_partitions.items():
        prefix = f"/sys/block/mmcblk0/mmcblk0p{partition}/"
        if adb_query(args.transport, "cat " + prefix + "start " + prefix + "size").split() != [str(start), str(size)]:
            raise ValueError("STOP: partition layout mismatch")
    for area in ("boot0", "boot1"):
        manifest, image = manifests[area]
        verify_gzip(image, manifest["raw_bytes"], manifest["sha256"])
        if device_hash(args.transport, AREAS[area][0]) != manifest["sha256"]:
            raise ValueError("STOP: hardware boot-area re-read mismatch")
        print(area + " independent re-read matched.", flush=True)
    manifest, image = manifests["emmc"]
    ranges = {name: (offset, length) for name, (_, _, length, offset) in SAMPLES.items()}
    print("Re-reading full compressed image and hashing sample ranges.", flush=True)
    expected = hash_ranges(image, ranges, manifest["raw_bytes"], manifest["sha256"])
    for name, (device, start, length, _) in SAMPLES.items():
        pipeline = (
            "set -o pipefail || exit 97; "
            f"/system/bin/busybox dd if=/dev/block/{device} bs=65536 skip={start // 65536} count={length // 65536} 2>/dev/null | "
            "/system/bin/busybox sha256sum; result=$?; echo RANGE_STATUS:$result"
        )
        output = adb_query(args.transport, "/system/bin/busybox sh -c " + shlex.quote(pipeline))
        lines = output.splitlines()
        if len(lines) != 2 or lines[1].strip() != "RANGE_STATUS:0":
            raise ValueError("Independent range read failed")
        match = re.fullmatch(r"([0-9a-f]{64})\s+[-]", lines[0].strip())
        if not match or match.group(1) != expected[name]:
            raise ValueError("STOP: independent sample mismatch: " + name)
        print(name + " independent re-read matched.", flush=True)
    os.umask(0o077)
    report = {
        "verified_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "emmc_raw_bytes": manifest["raw_bytes"],
        "whole_image_sha256": manifest["sha256"],
        "matched_sample_hashes": expected,
        "hardware_boot_areas_reverified": True,
        "live_capture": True,
        "atomic_snapshot": False,
        "restore_tested": False,
    }
    with (base / names["emmc"] / "verification.json").open("x") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print("All independent comparisons passed. Private report saved; restore remains untested.", flush=True)


if __name__ == "__main__":
    main()
