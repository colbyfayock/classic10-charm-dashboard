# Dragon Touch Classic10 Charm device record

This document contains sanitized observations from one unit. Devices sold under the same retail name may contain different hardware or firmware. Confirm every identity field before applying instructions.

## Purchase reference

Owner-confirmed purchased listing:
[Dragon Touch 10.1-inch Wi-Fi Digital Picture Frame — 1280×800 HD IPS touchscreen](https://www.amazon.com/dp/B0D9Q89D3K)
(Amazon ASIN `B0D9Q89D3K`). The title is the description supplied by the owner;
the current listing has not been independently checked.

Metadata the owner reports copying from the Amazon product page:

| Field | Reported value |
| --- | --- |
| Manufacturer | Dragon Touch |
| Amazon-reported model number | `809cfd61-b795-4488-81bb-c20ec48e6016` |
| UPC | `850045550981` |

The UPC has a valid UPC-A check digit; that checks its format, not product identity
or hardware compatibility. These catalog details do not replace the Android model
and firmware identity measured below.

The UUID-shaped model number is recorded as a shared listing/catalog field based
on the owner's source confirmation, not as a device serial or the Android model.

This identifies the purchased product listing, not a guarantee that other units
ship with the same board, Android version, firmware, or access method. No order,
account, or unique device details are included.

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

Network access has also failed intermittently between sessions. Address changes,
host-specific ADB failures, and unresolved LAN reachability have been observed;
there is no confirmed single root cause. See [connection troubleshooting](connection-troubleshooting.md)
before repeating reboots, changing ADB configuration, or applying another frame's fixes.

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
- Owner reports a full-size USB-A socket and a mini-USB socket. The mini-USB port
  is the candidate for testing a computer data connection; device-mode wiring is
  not yet verified. Do not use a USB-A-to-A connection between host ports.
- Several USB Ethernet modules are loaded; adapter operation is untested.
- SystemUI is installed and in its default enabled state. A status-bar window is
  present in window policy. Physical navigation and escape paths are not yet proven.

VPhoto declares the normal Home component
`com.waophoto.smartframe/.ui.SplashActivity`. Additional Home declarations belong
to Android's provisioning and encryption components, not general-purpose launchers.
The stock Settings component is `com.android.settings/.Settings`; Browser declares
`com.android.browser/.BrowserActivity`.

### Navigation tests on the stock firmware

- Explicitly launching `com.android.settings/.Settings` opened Android Settings;
  the owner confirmed it was visible on the physical panel.
- The owner reported no obvious physical or on-screen Back/Home control there.
- Explicitly launching `com.waophoto.smartframe/.ui.SplashActivity` returned to
  VPhoto's `.ui.MainActivity`; the owner confirmed the photo application was visible.
- Invoking MAIN with the HOME category resolved to VPhoto. The saved preferred
  activity records and VPhoto/SystemUI/Settings enabled states were unchanged.
- `qemu.hw.mainkeys` was unset. This does not establish a safe runtime toggle for
  the navigation bar or prove what firmware resource controls its absence.

An exact private package-state baseline was saved before the tests. No app was
installed or disabled and no default Home was changed. ADB fallback is proven, but
**a physical escape path from other apps is not yet established**. Provide and test
usable touch navigation before replacing Home or treating this as a general-purpose
browser device. Browser and firmware recovery behavior remain untested.

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
  shell transfer was subsequently used for the verified chunked capture below.
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

The initial single-stream eMMC attempt was stopped at the owner's request before
completion. Its retained `.partial` file is not a verified backup and cannot be
resumed by the chunked tool. That attempt never passed full-image verification. See
[host backup tools](../tools/README.md) for capture and verification commands.
No images or capture hashes are included in this repository.

A resumable replacement now captures independently verified 64 MiB eMMC chunks
with private atomic checkpoints. Host-side interruption/resume tests pass. Two
bounded hardware runs also passed: the first captured boot0 and stopped; the second
revalidated and skipped boot0, captured boot1, and stopped. Both boot areas matched
independent device hashes. On 2026-10-17, the resumable session completed all
237 parts: 235 eMMC chunks plus both hardware boot areas.

Final verification passed:

- Exact, gap-free coverage of 15,758,000,128 user-area bytes and both 4,194,304-byte
  hardware boot areas.
- Full gzip readback, raw SHA-256 checks, and uniform-filler checks for every chunk.
- Fresh device hashes matched both hardware boot areas.
- Seven independent device reads matched saved image ranges: disk header,
  bootloader, env, boot, recovery, and two 32 MiB system samples.

The complete session occupies approximately 325.5 MiB compressed on this unit.
All images and private checkpoints remain owner-only and Git-ignored. The prior
interrupted attempt is retained separately and must not be mistaken for this
verified session. This is a **verified live capture, not an atomic filesystem
snapshot**. Firmware restore and recovery flashing remain untested; successful
capture is not proof that a device can be restored from it.

## Current verification status

- Device identity: verified
- Root network ADB: verified
- Persistence after software reboot: verified
- Persistence after power loss: verified on this unit
- Static storage and hardware inventory: complete on this unit
- Settings/VPhoto ADB navigation: tested with owner screen confirmation
- Physical Back/Home navigation: unavailable in the tested Settings screen; unresolved
- Recovery entry and browser rendering: not tested
- Hardware boot-area backups: captured and verified
- Full eMMC backup and independent partition comparisons: passed on this unit
- Firmware restore: not tested
- Dashboard browser selection: pending
- Automatic dashboard startup: pending
