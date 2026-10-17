# Dragon Touch Classic10 Charm device record

This document contains sanitized observations from one unit. Devices sold under the same retail name may contain different hardware or firmware. Confirm every identity field before applying instructions.

## Identity

| Property | Observed value |
| --- | --- |
| Model | `Classic10 charm` |
| Firmware | `Classic10-charm-A33-4.4.2.20240619_V03` |
| Android | 4.4.2 / API 19 |
| Fingerprint | `Allwinner/astar_ococci/astar-ococci:4.4.2/KVT49L/20240619:eng/test-keys` |
| Manufacturer property | `softwinner` |
| Board platform | `polaris` |
| Hardware property | `sun8i` |
| CPU ABI | `armeabi-v7a` |
| Display | 1280×800 at 160 dpi |
| RAM | Approximately 1 GB |
| eMMC | Approximately 16 GB |
| Stock Home app | VPhoto 2.1.3.34, `com.waophoto.smartframe` |
| OTA updater | ADUPS FOTA, `com.adups.fota` |
| SELinux | Permissive |

The firmware name and platform properties are consistent with an Allwinner A33-family board. The chip has not yet been physically inspected.

## ADB access

The tested unit listens on TCP 5555 after boot and returns a root shell:

```sh
adb connect FRAME_ADDRESS:5555
adb -s FRAME_ADDRESS:5555 shell id
```

Observed properties:

```text
ro.adb.secure=0
service.adb.tcp.port=5555
uid=0(root) gid=0(root)
```

Root network ADB returned after both a software reboot and an owner-confirmed
physical power disconnection of more than 15 seconds. After reconnection, the model
and firmware matched, boot completion was reported, and the shell was still root.
No USB connection, boot patch, vendor command, or on-screen authorization was required.

## Compatibility notes

- The upstream Home HQ kiosk currently requires API 23 and cannot install on this API 19 frame.
- Current Firefox releases require a newer Android version.
- The stock Android 4.4 browser/WebView is expected to require a legacy-compatible dashboard build.
- No firmware flash or boot patch is needed to obtain root management access on the tested unit.

## Storage layout

The user-area disk is `/dev/block/mmcblk0`, with 30,777,344 sectors of 512 bytes:
**15,758,000,128 bytes**. Each hardware boot area (`mmcblk0boot0` and
`mmcblk0boot1`) is **4,194,304 bytes**, with `ro=1` and `force_ro=1` when inspected.

Partition names came from `/dev/block/by-name`; starts and sizes came from sysfs.
These are observations, not a flashing procedure.

| Partition | Name | Start sector | Size in sectors | Size in MiB |
| --- | --- | ---: | ---: | ---: |
| p2 | bootloader | 73728 | 131072 | 64 |
| p5 | env | 204800 | 32768 | 16 |
| p6 | boot | 237568 | 32768 | 16 |
| p7 | system | 270336 | 1572864 | 768 |
| p8 | misc | 1843200 | 32768 | 16 |
| p9 | recovery | 1875968 | 65536 | 32 |
| p10 | cache | 1941504 | 1048576 | 512 |
| p11 | metadata | 2990080 | 32768 | 16 |
| p12 | private | 3022848 | 32768 | 16 |
| p13 | klog | 3055616 | 32768 | 16 |
| p14 | alog | 3088384 | 131072 | 64 |
| p1 | UDISK | 3219456 | 27557888 | 13456 |

The kernel also exposes an unnamed p3 entry at sector 1 with size 2 sectors. Its
meaning has not been established; do not treat it as an independently understood
data partition.

> [!WARNING]
> This firmware's boot partition starts at sector **237568**, not the **172032**
> used by the PF1007L guides. Do not apply their offsets, boot images, or write scripts.

Observed mounts:

- `/system`: ext4, read-only, from `system`.
- `/data`: ext4, read-write, from `UDISK`.
- `/cache`: ext4, read-write, from `cache`.
- `/logger`: ext4, read-write, from `alog`.

Android remains running during inspection. A live capture of writable filesystems
will not automatically be an atomic offline snapshot.

## Hardware and navigation inventory

- Kernel: Linux 3.4.39.
- Wi-Fi: ESP8089 module, interface `wlan0`, SDIO vendor/device `0x6666:0x1111`.
- Touchscreen: `gslX680`, with the `gslX680new` module loaded.
- Sensor service reports a temperature sensor, a `pt3r850` light sensor, and a
  `mir3da` accelerometer. The accelerometer was active; light/temperature behavior
  has not been physically tested. Sensor names alone do not establish their usefulness.
- USB gadget settings report `mtp,adb`, with driver `sunxi_usb_udc`. Physical USB
  data access is untested.
- Several USB Ethernet modules are loaded; adapter operation is untested.
- SystemUI is installed and in its default enabled state. A status-bar window is
  present in window policy. Physical navigation and escape paths are not yet proven.

VPhoto declares the normal Home component
`com.waophoto.smartframe/.ui.SplashActivity`. Additional Home declarations belong
to Android's provisioning and encryption components, not general-purpose launchers.
The stock Settings component is `com.android.settings/.Settings`; Browser declares
`com.android.browser/.BrowserActivity`. These were identified from package metadata,
not launched or tested for physical recovery.

## Browser and clock baseline

AOSP Browser reports Android 4.4.2 / API 19. WebView is integrated through
`/system/lib/libwebviewchromium.so` and `/system/framework/webviewchromium.jar`.
The exact Chromium engine version and dashboard rendering compatibility remain
unmeasured; a package version alone is not an engine capability test.

Automatic time and automatic timezone settings are enabled. The device UTC clock
matched the host to the displayed second when queried after boot. Initial cold-boot
time, synchronization delay, and RTC persistence remain untested.

## Read-only transfer capabilities

- This daemon rejects `adb exec-out` with `error: closed`.
- `adb shell -T` fails because only a PTY is supported. Do not stream raw disk images
  through a regular shell; terminal processing may corrupt binary bytes.
- BusyBox exists at `/system/bin/busybox`, including `dd`, `gzip`, `sha256sum`,
  `md5sum`, `hexdump`, `od`, and `tar`. It is not at `/system/xbin/busybox`.
- `adb pull` transferred the 5,360-byte `/system/bin/reboot` executable to temporary
  host storage; host and device SHA-256 matched. The host copy was then removed.
  This verifies a small regular-file transfer, not a complete block-device backup.
- A synthetic four-byte payload containing NUL, LF, CR, and a high byte survived
  BusyBox hexadecimal encoding, PTY transfer, and host decoding exactly. Encoded
  shell transfer is a fallback candidate, not yet a tested full-disk capture path.
- Recovery executable `/system/bin/recovery` is present. Recovery entry, behavior,
  and restore have not been tested; no recovery reboot was performed.

### Capture observations

Both 4 MiB hardware boot areas have been captured privately. Each passed exact-size
checks, matching independent device SHA-256 before and after transfer, complete gzip
readback, and uniform-filler checks.

Legacy ADB sync took approximately 27 seconds per boot area. Enabling TCP_NODELAY
on the host relay did not improve this measurement. Device-side gzip plus hex
encoding captured one boot area in approximately 0.88 seconds and matched the sync
capture and independent device hashes. These small, highly compressible captures
do not predict an exact completion time for the whole disk.

The full eMMC capture was stopped at the owner's request before completion. The
retained `.partial` file is not a verified backup, and the current tool cannot
resume it. Independent whole-image partition comparisons have not passed. See
[host backup tools](../tools/README.md) for capture and verification commands.
No images or capture hashes are included in this repository.

A resumable replacement now captures independently verified 64 MiB eMMC chunks
with private atomic checkpoints. Its host-side interruption/resume tests pass;
initial hardware checkpoint testing is pending device connectivity. The prior
interrupted single-stream capture and verified hardware boot-area copies remain
untouched. See the host tools guide for start/resume commands and snapshot limits.

## Current verification status

- Device identity: verified
- Root network ADB: verified
- Persistence after software reboot: verified
- Persistence after power loss: verified on this unit
- Static storage and hardware inventory: complete on this unit
- Physical navigation, recovery entry, and browser rendering: deferred until after backup
- Hardware boot-area backups: captured and verified
- Full eMMC backup and independent partition comparisons: incomplete; stopped by owner
- Dashboard browser selection: pending
- Automatic dashboard startup: pending
