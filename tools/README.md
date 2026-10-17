# Host tools

Host-side utilities in this directory must be device-agnostic, avoid embedding private addresses or identifiers, and bind local network services to loopback by default.

## ADB TCP relay

`adb_tcp_relay.py` forwards a localhost port to a frame's ADB port. It exists for macOS environments where ordinary TCP clients can reach the frame but the ADB daemon reports `No route to host`.

```sh
python3 tools/adb_tcp_relay.py FRAME_ADDRESS
adb connect 127.0.0.1:15555
```

The relay accepts a new ADB client after a disconnect or frame reboot. Stop it with `Ctrl-C` when the management session ends.

## Read-only backup capture

`backup_frame.py` is restricted to the model, firmware, capacities, and boot offset
documented in [the device record](../docs/device.md). It contains no device write
commands and creates private output only under ignored, owner-only `backups/`.
Each session directory must be new; existing captures are never overwritten.

```sh
python3 tools/backup_frame.py --area boot0 --session boot0-initial
python3 tools/backup_frame.py --area boot1 --session boot1-initial
python3 tools/backup_frame.py --area emmc --method encoded --session emmc-initial
```

The default `sync` method uses the legacy binary file-transfer protocol, not a PTY.
The `encoded` method uses existing BusyBox tools to read bounded blocks, compress
them, and send hexadecimal text through the legacy shell. It checks the complete
pipeline exit status, decoded length, gzip integrity, and raw SHA-256. The encoded
method matched an independent sync capture and on-device checksums for one hardware
boot area on the tested unit. No tool is installed on the frame.

Both methods verify full compressed readback and reject complete 64 KiB uniform
filler blocks. Failed captures retain `.partial` files, which must not be treated
as verified backups. Hardware boot-area captures also require matching device
hashes before and after transfer. Whole-disk captures are live and require the
additional independent verification below.

## Independent backup verification

After all three captures have completed, run:

```sh
python3 tools/verify_frame_backup.py
```

The verifier rechecks device identity and relevant partition offsets, revalidates
both hardware boot-area images against fresh device hashes, reads the entire eMMC
gzip again, and compares seven stable image ranges with fresh reads from the frame.
Its private result is written to `backups/emmc-initial/verification.json`.

Manifests contain private whole-disk hashes and must never be published. A verified
live capture is not an atomic filesystem snapshot and does not establish that
firmware restoration works. No restore tool or flashing procedure is provided.
