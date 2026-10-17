#!/usr/bin/env python3
"""Resumable, read-only captures of the exact Classic10 Charm unit under test."""

import argparse
from contextlib import contextmanager
import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import time
import uuid

from backup_frame import AREAS, FIRMWARE, MODEL, adb_query, assert_identity, capture, device_hash, verify_gzip
from verify_frame_backup import SAMPLES


STORAGE_LAYOUT = {
    1: (3219456, 27557888), 2: (73728, 131072), 5: (204800, 32768),
    6: (237568, 32768), 7: (270336, 1572864), 8: (1843200, 32768),
    9: (1875968, 65536), 10: (1941504, 1048576), 11: (2990080, 32768),
    12: (3022848, 32768), 13: (3055616, 32768), 14: (3088384, 131072),
}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@contextmanager
def capture_lock(base):
    lock_path = base / ".chunked-capture.lock"
    if lock_path.is_symlink():
        raise ValueError("Refusing a symlinked capture lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another chunked backup is already running") from error
        yield


def make_plan(chunk_bytes):
    if chunk_bytes < 65536 or chunk_bytes % 65536:
        raise ValueError("Chunk size must be a positive multiple of 64 KiB")
    plan = []
    for area, (_, total) in AREAS.items():
        for index, offset in enumerate(range(0, total, chunk_bytes)):
            plan.append({
                "area": area, "offset": offset,
                "size": min(chunk_bytes, total - offset),
                "file": f"{area}-{index:06d}.img.gz",
            })
    return plan


def save_checkpoint(folder, state):
    temporary = folder / ("checkpoint-" + uuid.uuid4().hex + ".tmp")
    with temporary.open("x") as output:
        json.dump(state, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, folder / "checkpoint.json")
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def preserve_unfinished(folder, item):
    for name in (item["file"], item["file"] + ".partial"):
        old = folder / name
        if old.is_symlink():
            raise ValueError("Refusing a symlinked capture file")
        if old.exists():
            archive = folder / "interrupted"
            if archive.is_symlink():
                raise ValueError("Refusing a symlinked archive directory")
            archive.mkdir(mode=0o700, exist_ok=True)
            old.rename(archive / (name + "." + uuid.uuid4().hex))
            print("Preserved an unfinished attempt; retrying this chunk.", flush=True)


def run_session(folder, identity, plan, reader, max_new_chunks=None):
    checkpoint = folder / "checkpoint.json"
    if checkpoint.is_symlink():
        raise ValueError("Refusing a symlinked checkpoint")
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text())
        if state.get("schema") != 1 or state.get("identity") != identity or state.get("plan") != plan:
            raise ValueError("STOP: saved device identity or chunk plan mismatch")
    else:
        state = {"schema": 1, "identity": identity, "plan": plan, "completed": {}, "created_utc": now()}
    completed = state.get("completed")
    if not isinstance(completed, dict) or set(completed) - {item["file"] for item in plan}:
        raise ValueError("Invalid completed-chunk index")
    # Never trust a progress flag without checking the actual saved gzip again.
    for item in plan:
        record = completed.get(item["file"])
        if record is not None:
            image = folder / item["file"]
            if (image.is_symlink() or record.get("offset") != item["offset"]
                    or record.get("size") != item["size"]
                    or not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", ""))):
                raise ValueError("Invalid saved chunk metadata")
            verify_gzip(image, item["size"], record["sha256"])
    state["status"] = "capturing"
    state["updated_utc"] = now()
    save_checkpoint(folder, state)
    print(f"Resume check passed: {len(completed)} of {len(plan)} chunks already verified.", flush=True)
    new_chunks = 0
    try:
        for item in plan:
            if item["file"] in completed:
                continue
            if max_new_chunks is not None and new_chunks >= max_new_chunks:
                state["status"] = "paused"
                break
            preserve_unfinished(folder, item)
            print(f"Starting {item['area']} chunk at {item['offset'] // 1048576} MiB ({item['size'] // 1048576} MiB).", flush=True)
            started = time.monotonic()
            digest = reader(item, folder / item["file"])
            verify_gzip(folder / item["file"], item["size"], digest)
            completed[item["file"]] = {
                "offset": item["offset"], "size": item["size"], "sha256": digest,
                "completed_utc": now(), "elapsed_seconds": round(time.monotonic() - started, 2),
            }
            state["updated_utc"] = now()
            save_checkpoint(folder, state)
            new_chunks += 1
            total = sum(record["size"] for record in completed.values())
            print(f"Checkpoint saved: {len(completed)}/{len(plan)} chunks, {total / 1048576:.1f} MiB verified locally.", flush=True)
        else:
            state["status"] = "capture_complete_pending_independent_verification"
    except BaseException as error:
        state["status"] = "paused" if isinstance(error, KeyboardInterrupt) else "failed"
        state["error_type"] = type(error).__name__
        state["updated_utc"] = now()
        save_checkpoint(folder, state)
        raise
    state["updated_utc"] = now()
    save_checkpoint(folder, state)
    return state


def private_fingerprint(transport):
    cid = adb_query(transport, "cat /sys/block/mmcblk0/device/cid")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", cid):
        raise ValueError("Cannot establish private physical-device identity")
    # A CID fingerprint is itself private. Store it only inside the ignored checkpoint.
    return hashlib.sha256((MODEL + FIRMWARE + cid.lower()).encode()).hexdigest()


def physical_identity(transport):
    assert_identity(transport)
    for partition, expected in STORAGE_LAYOUT.items():
        prefix = f"/sys/block/mmcblk0/mmcblk0p{partition}/"
        if adb_query(transport, "cat " + prefix + "start " + prefix + "size").split() != [str(value) for value in expected]:
            raise ValueError("STOP: partition layout mismatch")
    return private_fingerprint(transport)


def verify_session(folder, state, transport):
    if len(state["completed"]) != len(state["plan"]):
        raise ValueError("Cannot verify an incomplete capture")
    if physical_identity(transport) != state["identity"]:
        raise ValueError("STOP: physical device identity changed")
    partitions = {2: (73728, 131072), 5: (204800, 32768), 6: (237568, 32768), 7: (270336, 1572864), 9: (1875968, 65536)}
    for partition, expected in partitions.items():
        prefix = f"/sys/block/mmcblk0/mmcblk0p{partition}/"
        observed = adb_query(transport, "cat " + prefix + "start " + prefix + "size").split()
        if observed != [str(value) for value in expected]:
            raise ValueError("STOP: independent verification partition mismatch")
    hashes = {name: hashlib.sha256() for name in SAMPLES}
    counts = {name: 0 for name in SAMPLES}
    whole = hashlib.sha256()
    area_hashes = {area: hashlib.sha256() for area in ("boot0", "boot1")}
    print("Re-reading saved chunks for full coverage and independent sample hashes.", flush=True)
    for item in state["plan"]:
        offset = item["offset"]
        digest = hashlib.sha256()
        with gzip.open(folder / item["file"], "rb") as source:
            while True:
                data = source.read(65536)
                if not data:
                    break
                if data == bytes([204]) * 65536:
                    raise ValueError("Suspicious uniform filler block")
                digest.update(data)
                if item["area"] == "emmc":
                    whole.update(data)
                    for name, (_, _, length, start) in SAMPLES.items():
                        left, right = max(offset, start), min(offset + len(data), start + length)
                        if right > left:
                            sample = data[left - offset:right - offset]
                            hashes[name].update(sample)
                            counts[name] += len(sample)
                else:
                    area_hashes[item["area"]].update(data)
                offset += len(data)
        record = state["completed"][item["file"]]
        if offset != item["offset"] + item["size"] or digest.hexdigest() != record["sha256"]:
            raise ValueError("Saved chunk changed during final verification")
    for area, digest in area_hashes.items():
        if device_hash(transport, AREAS[area][0]) != digest.hexdigest():
            raise ValueError("STOP: hardware boot-area re-read mismatch")
    for name, (device, start, length, _) in SAMPLES.items():
        if counts[name] != length:
            raise ValueError("Incomplete image sample coverage")
        pipeline = (
            "set -o pipefail || exit 97; "
            f"/system/bin/busybox dd if=/dev/block/{device} bs=65536 skip={start // 65536} count={length // 65536} 2>/dev/null | "
            "/system/bin/busybox sha256sum; result=$?; echo RANGE_STATUS:$result"
        )
        lines = adb_query(transport, "/system/bin/busybox sh -c " + shlex.quote(pipeline)).splitlines()
        if (len(lines) != 2 or lines[1].strip() != "RANGE_STATUS:0"
                or lines[0].split()[0] != hashes[name].hexdigest()):
            raise ValueError("STOP: independent sample mismatch: " + name)
        print(name + " independent re-read matched.", flush=True)
    state.update({
        "status": "verified_live_capture", "verified_utc": now(),
        "whole_image_sha256": whole.hexdigest(),
        "independent_samples": {name: digest.hexdigest() for name, digest in hashes.items()},
        "atomic_snapshot": False, "restore_tested": False,
    })
    save_checkpoint(folder, state)
    print("Full coverage, gzip checks, and independent comparisons passed. Restore is not tested.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="127.0.0.1:15555")
    parser.add_argument("--session", default="chunked-v1")
    parser.add_argument("--chunk-mib", type=int, default=64)
    parser.add_argument("--max-new-chunks", type=int)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.session):
        parser.error("Session must be a simple directory name")
    if args.max_new_chunks is not None and args.max_new_chunks < 1:
        parser.error("Chunk limit must be positive")
    plan = make_plan(args.chunk_mib * 1048576)
    root = Path(__file__).resolve().parents[1]
    base = root / "backups"
    if base.is_symlink() or not base.is_dir() or stat.S_IMODE(base.stat().st_mode) != 0o700:
        raise ValueError("Backup parent must be owner-only and not a symlink")
    if subprocess.run(["git", "check-ignore", "--quiet", "backups/" + args.session + "/checkpoint.json"], cwd=root).returncode:
        raise ValueError("Backup session must be Git-ignored")
    if subprocess.check_output(["git", "ls-files", "backups"], cwd=root).strip():
        raise ValueError("STOP: private backup artifacts are tracked")
    if shutil.disk_usage(base).free < sum(size for _, size in AREAS.values()) + 5 * 1024 ** 3:
        raise ValueError("Insufficient free space with safety margin")
    os.umask(0o077)
    folder = base / args.session
    if folder.is_symlink():
        raise ValueError("Refusing a symlinked session")
    folder.mkdir(mode=0o700, exist_ok=True)
    if stat.S_IMODE(folder.stat().st_mode) != 0o700:
        raise ValueError("Session directory must be owner-only")
    def interrupt(signum, frame):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, interrupt)
    with capture_lock(base):
        identity = physical_identity(args.transport)

        def reader(item, destination):
            if private_fingerprint(args.transport) != identity:
                raise ValueError("STOP: physical device changed before capture")
            source = AREAS[item["area"]][0]
            hardware_area = item["area"] != "emmc" and item["size"] == AREAS[item["area"]][1]
            before = device_hash(args.transport, source) if hardware_area else None
            digest = capture(args.transport, source, item["size"], destination, "encoded", item["offset"])
            if private_fingerprint(args.transport) != identity:
                raise ValueError("STOP: physical device changed during capture")
            if hardware_area and (before != digest or device_hash(args.transport, source) != digest):
                raise ValueError("STOP: independent hardware boot-area hash mismatch")
            return digest

        try:
            state = run_session(folder, identity, plan, reader, args.max_new_chunks)
            if len(state["completed"]) == len(plan):
                try:
                    verify_session(folder, state, args.transport)
                except Exception as error:
                    state["status"] = "independent_verification_failed"
                    state["error_type"] = type(error).__name__
                    save_checkpoint(folder, state)
                    raise
            else:
                print("Paused at requested chunk limit; rerun the same session to resume.", flush=True)
        except KeyboardInterrupt:
            print("Stopped. Completed checkpoints are preserved; unfinished chunk will be retried.", flush=True)
            raise SystemExit(130)


if __name__ == "__main__":
    main()
