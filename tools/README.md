# Host tools

Host-side utilities in this directory must be device-agnostic, avoid embedding private addresses or identifiers, and bind local network services to loopback by default.

## Find a known device by MAC

```sh
python3 tools/find_device.py photo-frame --check
python3 tools/find_device.py photo-frame
python3 tools/find_device.py photo-frame --json
```

The finder uses an approved private MAC/network profile and one bounded ARP scan,
with native Mac administrator approval when needed. It refuses scope/tool changes,
keeps inventory private, and reports ambiguity instead of choosing arbitrarily.
`--check` never scans. It does not connect ADB or alter a device. See the
[discovery guide](../docs/device-discovery.md) for setup boundaries, exit codes,
privacy, validation evidence, and the difference between lookup and authentication.

## ADB TCP relay

`adb_tcp_relay.py` forwards a localhost port to a frame's ADB port. It exists for macOS environments where ordinary TCP clients can reach the frame but the ADB daemon reports `No route to host`.

```sh
python3 tools/adb_tcp_relay.py FRAME_ADDRESS
adb connect 127.0.0.1:15555
```

The relay accepts a new ADB client after a disconnect or frame reboot. Stop it with `Ctrl-C` when the management session ends.

## Read-only backup capture

### Resumable chunked capture (recommended)

```sh
python3 tools/chunked_backup.py --session chunked-v1
```

Rerun exactly the same command to resume. It rechecks device identity, partition
layout, and all completed gzip files before skipping verified chunks. The private
checkpoint also binds the session to the physical eMMC, not just a model name or
network address. Do not publish that checkpoint.

The default plan contains 235 eMMC chunks of at most 64 MiB plus two 4 MiB hardware
boot areas. Each completed chunk passes exact-size, gzip, SHA-256, and filler checks
before an atomic checkpoint is saved. No raw device write commands are used.

To stop, press `Ctrl-C` in its terminal or send SIGINT/SIGTERM to the capture's
Python process. Completed checkpoints remain usable. The unfinished attempt is
preserved separately and retried on the next run. Corrupt completed files, changed
identity/layout, or a changed chunk plan stop the run rather than silently bypassing
verification. A capture lock prevents simultaneous chunked runs.

For a bounded initial test or a planned pause between chunks:

```sh
python3 tools/chunked_backup.py --session chunked-v1 --max-new-chunks 1
```

When all chunks are present, the tool automatically re-reads every chunk, verifies
full coverage, compares both hardware boot areas with fresh device hashes, and
compares seven stable eMMC ranges with independent device reads. Only then does
the private checkpoint report `verified_live_capture`. Local chunk completion alone
is not that final verification. A 180-second idle-output timeout prevents a silent
ADB stream from blocking forever.

Chunking does not guarantee greater speed. A resumed live capture can span multiple
device boots and changing filesystems; it is **not an atomic offline snapshot** and
restore remains untested. Do not install/change software or alter firmware while
capturing. Keep the frame powered, Wi-Fi connected, and the Mac awake.

### Original single-stream capture

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
