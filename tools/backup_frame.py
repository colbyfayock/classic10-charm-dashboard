#!/usr/bin/env python3
"""Read this tested frame through legacy ADB sync; never write to the device."""

import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import socket
import stat
import struct
import subprocess
import time
import zlib


MODEL = "Classic10 charm"
FIRMWARE = "Classic10-charm-A33-4.4.2.20240619_V03"
AREAS = {
    "boot0": ("/dev/block/mmcblk0boot0", 4194304),
    "boot1": ("/dev/block/mmcblk0boot1", 4194304),
    "emmc": ("/dev/block/mmcblk0", 15758000128),
}


def read_exact(stream, size):
    data = bytearray()
    while len(data) < size:
        part = stream.recv(size - len(data))
        if not part:
            raise ValueError("Truncated ADB stream")
        data.extend(part)
    return bytes(data)


def receive_stream(stream, sink, expected_size):
    """Bound every packet and reject early EOF or extra bytes before success."""
    digest = hashlib.sha256()
    received = 0
    last_report = time.monotonic()
    while True:
        kind, size = struct.unpack("<4sI", read_exact(stream, 8))
        if kind == b"DONE":
            if size != 0 or received != expected_size:
                raise ValueError("Unexpected final byte count")
            return digest.hexdigest()
        if kind == b"FAIL":
            raise ValueError("ADB device rejected read request")
        if kind != b"DATA" or size == 0 or size > 65536:
            raise ValueError("Invalid ADB sync packet")
        if received + size > expected_size:
            raise ValueError("ADB stream exceeds expected device size")
        data = read_exact(stream, size)
        sink.write(data)
        digest.update(data)
        received += size
        if time.monotonic() - last_report > 60:
            print(f"Captured {received / 1048576:.1f} MiB of {expected_size / 1048576:.1f} MiB", flush=True)
            last_report = time.monotonic()


def verify_gzip(path, expected_size, expected_digest):
    """Read the entire gzip, checking its CRC, exact raw size, SHA-256, and filler."""
    digest = hashlib.sha256()
    size = 0
    with gzip.open(path, "rb") as source:
        while True:
            data = source.read(65536)
            if not data:
                break
            if len(data) == 65536 and data == bytes([204]) * 65536:
                raise ValueError("Suspicious uniform filler block")
            size += len(data)
            if size > expected_size:
                raise ValueError("Gzip readback exceeds expected size")
            digest.update(data)
    if size != expected_size or digest.hexdigest() != expected_digest:
        raise ValueError("Gzip readback size or hash mismatch")


def receive_encoded(lines, sink, expected_size):
    """Decode only gzip hex plus an explicit successful device pipeline marker."""
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    digest = hashlib.sha256()
    received = 0
    finished = False
    last_report = time.monotonic()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if finished:
            raise ValueError("Unexpected output after capture marker")
        if line == b"CAPTURE_STATUS:0":
            finished = True
            continue
        if len(line) > 2048 or not re.fullmatch(b"(?:[0-9a-f]{2})+", line):
            raise ValueError("Invalid encoded capture output or failed pipeline")
        data = bytes.fromhex(line.decode("ascii"))
        sink.write(data)
        pending = data
        try:
            while pending:
                raw = decoder.decompress(pending, 1048576)
                pending = decoder.unconsumed_tail
                received += len(raw)
                if received > expected_size:
                    raise ValueError("Decoded stream exceeds expected size")
                digest.update(raw)
                if decoder.unused_data:
                    raise ValueError("Unexpected trailing compressed data")
        except zlib.error as error:
            raise ValueError("Corrupt compressed capture stream") from error
        if time.monotonic() - last_report > 60:
            print(f"Captured {received / 1048576:.1f} MiB of {expected_size / 1048576:.1f} MiB", flush=True)
            last_report = time.monotonic()
    if not finished or not decoder.eof or received != expected_size:
        raise ValueError("Incomplete encoded capture or missing success marker")
    return digest.hexdigest()


def adb_query(transport, command):
    result = subprocess.run(
        ["adb", "-s", transport, "shell", command],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise ValueError("ADB identity or checksum query failed")
    return result.stdout.strip()


def assert_identity(transport):
    expected = {
        "getprop ro.product.model": MODEL,
        "getprop ro.build.display.id": FIRMWARE,
        "getprop sys.boot_completed": "1",
        "cat /sys/block/mmcblk0/size": "30777344",
        "cat /sys/block/mmcblk0boot0/size": "8192",
        "cat /sys/block/mmcblk0boot1/size": "8192",
        "cat /sys/block/mmcblk0/mmcblk0p6/start": "237568",
    }
    for command, value in expected.items():
        if adb_query(transport, command) != value:
            raise ValueError("STOP: device identity or storage mismatch")
    if not adb_query(transport, "id").startswith("uid=0(root)"):
        raise ValueError("STOP: root access unavailable")


def device_hash(transport, path):
    value = adb_query(transport, "/system/bin/busybox sha256sum " + path)
    match = re.match(r"([0-9a-f]{64})\s", value)
    if not match:
        raise ValueError("Invalid device checksum response")
    return match.group(1)


def service(stream, name):
    payload = name.encode("utf-8")
    stream.sendall(f"{len(payload):04x}".encode("ascii") + payload)
    if read_exact(stream, 4) != b"OKAY":
        raise ValueError("ADB server rejected service selection")


def encoded_pipeline(path, expected_size, offset=0):
    sizes = {source: size for source, size in AREAS.values()}
    if (path not in sizes or offset < 0 or expected_size <= 0
            or offset % 65536 or expected_size % 65536
            or offset + expected_size > sizes[path]):
        raise ValueError("Read range must be aligned and within a known device")
    return (
        "set -o pipefail || exit 97; "
        f"/system/bin/busybox dd if={shlex.quote(path)} bs=65536 skip={offset // 65536} count={expected_size // 65536} 2>/dev/null | "
        "/system/bin/busybox gzip -1c | "
        "/system/bin/busybox hexdump -v -e '1024/1 \"%02x\" \"\\n\"'; "
        "result=$?; echo; echo CAPTURE_STATUS:$result"
    )


def encoded_lines(pipe, idle_timeout=180):
    """Bound both idle time and line length without buffered-pipe deadlocks."""
    pending = b""
    with selectors.DefaultSelector() as selector:
        selector.register(pipe, selectors.EVENT_READ)
        while True:
            if not selector.select(idle_timeout):
                raise TimeoutError("Capture stream idle timeout")
            block = os.read(pipe.fileno(), 65536)
            if not block:
                if pending:
                    yield pending
                return
            pending += block
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                if len(line) > 4096:
                    raise ValueError("Capture output line too long")
                yield line
            if len(pending) > 4096:
                raise ValueError("Capture output line too long")


def capture(transport, path, expected_size, destination, method="sync", offset=0):
    partial = destination.with_name(destination.name + ".partial")
    if method == "encoded":
        pipeline = encoded_pipeline(path, expected_size, offset)
        command = "/system/bin/busybox sh -c " + shlex.quote(pipeline)
        process = subprocess.Popen(
            ["adb", "-s", transport, "shell", command],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        try:
            with partial.open("xb") as output:
                lines = encoded_lines(process.stdout)
                digest = receive_encoded(lines, output, expected_size)
                output.flush()
                os.fsync(output.fileno())
            if process.wait(timeout=30):
                raise ValueError("Encoded ADB process failed")
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()
        verify_gzip(partial, expected_size, digest)
        if destination.exists():
            raise ValueError("Refusing to replace an existing capture")
        partial.rename(destination)
        return digest
    if offset:
        raise ValueError("Sync transfer does not support a partial device range")
    with socket.create_connection(("127.0.0.1", 5037), timeout=30) as stream:
        stream.settimeout(120)
        service(stream, "host:transport:" + transport)
        service(stream, "sync:")
        source = path.encode("utf-8")
        stream.sendall(b"RECV" + struct.pack("<I", len(source)) + source)
        with partial.open("xb") as output:
            with gzip.GzipFile(filename="", fileobj=output, mode="wb", compresslevel=1, mtime=0) as compressed:
                digest = receive_stream(stream, compressed, expected_size)
            output.flush()
            os.fsync(output.fileno())
    verify_gzip(partial, expected_size, digest)
    if destination.exists():
        raise ValueError("Refusing to replace an existing capture")
    partial.rename(destination)
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", default="127.0.0.1:15555")
    parser.add_argument("--area", choices=tuple(AREAS), required=True)
    parser.add_argument("--method", choices=("sync", "encoded"), default="sync")
    parser.add_argument("--session", required=True, help="New local backup-session directory name")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.session):
        parser.error("Session must be a simple directory name")
    root = Path(__file__).resolve().parents[1]
    base = root / "backups"
    if base.is_symlink() or not base.is_dir() or stat.S_IMODE(base.stat().st_mode) != 0o700:
        raise ValueError("Backup parent must be an owner-only, nonsymlink directory")
    ignored = subprocess.run(["git", "check-ignore", "--quiet", "backups/" + args.session + "/manifest.json"], cwd=root)
    if ignored.returncode or subprocess.check_output(["git", "ls-files", "backups"], cwd=root).strip():
        raise ValueError("Backup destination must be ignored and untracked")
    os.umask(0o077)
    folder = base / args.session
    folder.mkdir(mode=0o700, exist_ok=False)
    source, expected_size = AREAS[args.area]
    if shutil.disk_usage(folder).free < expected_size + 5 * 1024 ** 3:
        raise ValueError("Insufficient free space with safety margin")
    assert_identity(args.transport)
    original_hash = device_hash(args.transport, source) if args.area != "emmc" else None
    print("Identity confirmed; starting read-only " + args.area + " capture.", flush=True)
    started = time.monotonic()
    digest = capture(args.transport, source, expected_size, folder / (args.area + ".img.gz"), args.method)
    if original_hash is not None:
        if digest != original_hash or digest != device_hash(args.transport, source):
            raise ValueError("STOP: independent device hash mismatch")
    manifest = {
        "area": args.area,
        "method": args.method,
        "source": source,
        "raw_bytes": expected_size,
        "sha256": digest,
        "gzip_readback_verified": True,
        "uniform_filler_check_passed": True,
        "independent_device_hash_verified": original_hash is not None,
        "live_capture": True,
        "atomic_snapshot": False,
        "restore_tested": False,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with (folder / "manifest.json").open("x") as output:
        json.dump(manifest, output, indent=2)
        output.write("\n")
    print("Capture and compressed readback verified; private manifest saved. SHA-256 not printed.", flush=True)


if __name__ == "__main__":
    main()
