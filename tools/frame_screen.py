#!/usr/bin/env python3
"""Capture a private screen through legacy ADB; remove only our verified capture."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import zlib

from backup_frame import adb_query, assert_identity


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'backups' / 'screenshots'
TRANSPORT = '127.0.0.1:15555'


def decode_capture(output):
    """Require pipeline success and validate every PNG chunk before saving."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or lines[-1] != 'SCREEN_STATUS:0':
        raise ValueError('Capture pipeline failed')
    encoded = ''.join(lines[:-1])
    if len(encoded) > 16 * 1024 * 1024 or not re.fullmatch(r'(?:[0-9a-f]{2})+', encoded):
        raise ValueError('Invalid or oversized screenshot output')
    data = bytes.fromhex(encoded)
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Missing PNG signature')
    offset = 8
    first = True
    while offset + 12 <= len(data):
        size = struct.unpack_from('>I', data, offset)[0]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError('Truncated PNG chunk')
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:end - 4]
        crc = struct.unpack_from('>I', data, end - 4)[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise ValueError('PNG CRC mismatch')
        if first and (kind != b'IHDR' or size != 13):
            raise ValueError('Missing PNG header')
        first = False
        if kind == b'IEND':
            if size or end != len(data):
                raise ValueError('Unexpected PNG trailing data')
            return data
        offset = end
    raise ValueError('Incomplete PNG')


def check_folder(folder):
    """Reject redirected paths; private captures must not follow directory symlinks."""
    for path in (folder, *folder.parents):
        if path.is_symlink():
            raise ValueError('Screenshot directory must not use symlinks')


def store_capture(folder, data):
    check_folder(folder)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.chmod(0o700)
    image = folder / 'current.png'
    marker = folder / 'current.json'
    if any(p.exists() or p.is_symlink() for p in (image, marker)):
        raise ValueError('Existing capture left untouched; review/cleanup first')
    record = json.dumps({'owner': 'frame_screen_v1', 'sha256': hashlib.sha256(data).hexdigest()})
    with marker.open('x') as stream:
        stream.write(record + '\n')
    marker.chmod(0o600)
    with image.open('xb') as stream:
        stream.write(data)
    image.chmod(0o600)


def cleanup(folder):
    """Never sweep directories or delete an unrecognized/modified screenshot."""
    check_folder(folder)
    image = folder / 'current.png'
    marker = folder / 'current.json'
    if not any(p.exists() or p.is_symlink() for p in (image, marker)):
        return
    if any(p.is_symlink() or not p.is_file() for p in (image, marker)):
        raise ValueError('Unrecognized capture; left untouched')
    record = json.loads(marker.read_text())
    if record.get('owner') != 'frame_screen_v1' or record.get('sha256') != hashlib.sha256(image.read_bytes()).hexdigest():
        raise ValueError('Capture ownership/hash mismatch; left untouched')
    image.unlink()
    marker.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture', 'cleanup'))
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == 'cleanup':
        cleanup(FOLDER)
        print('Known capture/sidecar removed; unrelated files untouched.')
        return
    check_folder(FOLDER)
    for path in (ROOT / 'backups', FOLDER / 'current.png', FOLDER / 'current.json'):
        if path.is_symlink():
            raise ValueError('Symlink target refused')
    if (ROOT / 'backups').exists():
        if (ROOT / 'backups').stat().st_mode & 0o077:
            raise ValueError('backups/ must be owner-only')
    else:
        (ROOT / 'backups').mkdir(mode=0o700)
    for name in ('current.png', 'current.json'):
        path = FOLDER / name
        subprocess.run(['git', 'check-ignore', '-q', str(path)], cwd=ROOT, check=True)
        if path.exists():
            raise ValueError('Review and clean up the existing capture first')
    assert_identity(TRANSPORT)
    if adb_query(TRANSPORT, 'getprop ro.build.version.sdk') != '19':
        raise ValueError('Android API mismatch')
    pipeline = (
        "set -o pipefail || exit 97; /system/bin/screencap -p | "
        "/system/bin/busybox hexdump -v -e '1024/1 \"%02x\" \"\\n\"'; "
        "result=$?; echo SCREEN_STATUS:$result"
    )
    result = subprocess.run(
        ['adb', '-s', TRANSPORT, 'shell', '/system/bin/busybox sh -c ' + shlex.quote(pipeline)],
        capture_output=True, text=True, timeout=45, check=True,
    )
    store_capture(FOLDER, decode_capture(result.stdout))
    print('Inspect backups/screenshots/current.png, then run cleanup immediately.')


if __name__ == '__main__':
    main()
