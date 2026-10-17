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

Root network ADB returned after a software reboot. A physical power-cycle was
requested, but completion was not explicitly confirmed; low uptime proves a recent
boot, not its cause. Power-loss persistence remains unverified. No USB connection,
boot patch, vendor command, or on-screen authorization was required.

## Compatibility notes

- The upstream Home HQ kiosk currently requires API 23 and cannot install on this API 19 frame.
- Current Firefox releases require a newer Android version.
- The stock Android 4.4 browser/WebView is expected to require a legacy-compatible dashboard build.
- No firmware flash or boot patch is needed to obtain root management access on the tested unit.

## Current verification status

- Device identity: verified
- Root network ADB: verified
- Persistence after software reboot: verified
- Persistence after power loss: pending explicit physical confirmation
- Complete partition inventory: pending
- Verified private backup: pending
- Dashboard browser selection: pending
- Automatic dashboard startup: pending
