# Replacement OS feasibility

Read-only assessment started 2026-10-17. **No replacement image has been proven
compatible with this Classic10 Charm. No OS image, SD boot payload, or RAM loader
has been executed, and no firmware has been flashed.**

## Goal

An owner-controlled OS with a credible maintenance and security path, not merely
root access, a factory reset, or a newer-looking launcher on obsolete vendor Android.
General-purpose browser usability is the intended outcome; a dedicated dashboard
is optional.

## Is the Modern10 Charm guide the same device?

The [upstream Modern10 Charm report](https://github.com/wesbos/photo-frame-dashboard/blob/main/docs/dragontouch-modern10-charm.md)
describes a close hardware/software relative, but not the configuration verified here:

| Field | This unit | Upstream tested unit |
| --- | --- | --- |
| Android model | `Classic10 charm` | `Modern10 charm` |
| Android / API | 4.4.2 / 19 | 6.0.1 / 23 |
| Manufacturer property | `softwinner` | `joyhong` |
| Board / hardware | `exdroid` / `sun8i` | `exdroid` / `sun8i` |
| Fingerprint platform | `astar_ococci` | `astar_ococci` |
| CPU ABI | `armeabi-v7a` | `armeabi-v7a` |
| Display / density | 1280×800 / 160 dpi | 1280×800 / 160 dpi |
| Vendor home | VPhoto | VPhoto |
| Vendor updater | `com.adups.fota` | `com.waophoto.fota` |

Shared Allwinner platform names, display dimensions, and CPU ABI make it a useful
comparison, not proof of identical PCB revision, panel, GPIO wiring, Wi-Fi, flash
layout, or interchangeable firmware. Board markings and board-specific configuration
have not yet been compared to that unit.

The guide does **not upgrade Android**. It installs a launcher and Firefox on its
existing Android 6. Its documented APKs require API 21, so they cannot simply be
installed on this API 19 unit. Follow-up GeckoView/kiosk work also retained the OS.
It publishes no tested Android-upgrade image or restore procedure for this Classic10.
Even matching its Android 6 setup would not by itself meet the goal of a maintained,
security-supported system.

### Use the Modern10 guide as the adaptation baseline

Do not treat the Classic10 as unrelated hardware or start the usability work from
scratch. Reuse the guide's approach, changing steps only where this unit's measured
properties or tested behavior require it:

| Guide step | Reuse or adaptation on this unit |
| --- | --- |
| Root ADB over Wi-Fi | Same approach; already verified here |
| Private full backup before modification | Same safety approach; complete here, with legacy transport and resumable capture adaptations |
| Install a general-purpose launcher | Same goal; choose and verify an API 19-compatible build rather than the documented API 21 Rootless APK |
| Firefox with its own rendering engine | Same approach worth assessing; the documented Firefox build needs API 21, so an API 19 candidate and its website/security limits must be researched |
| Keep VPhoto as fallback | Same approach; explicit Settings/VPhoto launches and Home resolution already tested here |
| Floating Back/Home controls | Same recovery requirement; use API 19-compatible implementation/permissions rather than assuming the newer kiosk fits |
| Disable the vendor updater | Same potential hardening action, but this unit has a different updater package; requires exact approval and undo, not a copied command |

The baseline is a browser/launcher procedure, not an OS upgrade image. Replacement
OS research is a separate track. Temporary stock-OS usability work must stay
reversible and must not be described as achieving the final security goal.

See [the researched interim setup](interim-setup.md) for exact candidate versions,
official-source pins, permission/security tradeoffs, and approval gates while waiting
for a mini-USB cable. That interim plan does not imply any firmware interchangeability.

## Verified prerequisites and constraints

Read-only identity queries matched the same physical device and private verified
backup before this assessment:

- Android 4.4.2 / API 19, ARMv7 userspace, kernel 3.4.39.
- Device `W08`, board `exdroid`, platform `polaris`, hardware `sun8i`.
- No exposed Treble, VNDK, or dynamic-partition properties.
- No `gsid`, `gsi_tool`, or the checked DSU installer path.
- No separate named vendor block partition; `/vendor` exists as a path, which is
  not proof of Treble support.
- No mounted device tree at the checked standard procfs/sysfs paths. This is
  consistent with old vendor configuration, not proof of the complete boot format.
- Boot-lock, AVB state, and Android security-patch properties were unset. **Unset
  does not mean unlocked, verified, or safe to flash.**
- Non-unique marker inspection of the private backup found `eGON.BT0`, `script.bin`,
  and a `U-Boot 2011.09` string in the initial eMMC region. These are offline
  observations, not a demonstrated boot/recovery path.
- Wi-Fi is ESP8089; touchscreen is GSL-family; approximately 1 GB RAM.
- Full user-area and hardware boot-area captures are verified, but restore is untested.
- Mini-USB data capability and removable-card boot behavior are not yet proven.

## Candidate paths

### Generic Android GSI / DSU

**Not a supported drop-in route on the observed stock setup.** Google's
[GSI compliance guidance](https://developer.android.com/topic/generic-system-image)
requires a compatible Treble/vendor and boot configuration. This unit does not
expose those prerequisites. Adding them would itself be a board-porting project,
not an ordinary system-image update.

### Device-specific newer Android

No known-compatible, maintained build for the measured Classic10/W08 configuration
has been identified in the sources reviewed so far. This is a bounded search result,
not a claim that a port is technically impossible or that no private vendor firmware exists.

The [LineageOS-on-Allwinner organization](https://github.com/lineageos-on-allwinner)
is not generic A33 support. The reviewed `ceres-common` configuration targets a
different platform and assumes dynamic partitions, vendor interfaces, and boot
structures not present here. It is not a flash candidate.

The Modern10 Android 6 report is a useful lead for hardware comparison or asking
the manufacturer about an exact-board upgrade, but its firmware is not a validated
Classic10 image and Android 6 is not a sufficient long-term security target.

### Native Linux from removable media

**Plausible research path; not yet compatible or safe to boot as-is.**

[pangoleen/ormarch-picture-frame](https://github.com/pangoleen/ormarch-picture-frame/tree/4207b5c2f6d6615bf6a18fb725cc7a77dd532065)
reports an experimental SD-only Arch Linux ARM/Omarchy setup on a different
PF1007L A33 frame, leaving eMMC unmodified by design. This is a concrete related
hardware lead, not a board match:

- Its image targets an 800×1280 DSI panel with specific panel initialization and
  power sequencing; our panel type, timing, rails, and wiring are not established.
- It uses AIC8800 Wi-Fi/Bluetooth; this unit uses ESP8089.
- Both mention Silead-family touch, but matching controller names do not establish
  interchangeable firmware/calibration or reset wiring.
- Its SPL DRAM settings, PMIC voltages, SD/USB wiring, and board device tree must
  not be copied without comparing this unit's configuration.
- USB rescue is part of its design; this unit's mini-USB device mode is untested.
- That project's README reports working desktop features on its unit; parts of the
  image-builder documentation explicitly remain emulator-only or unproven on a
  fresh physical rebuild. Do not collapse those evidence levels into a guarantee.

The [ESP8089 driver source](https://github.com/al177/esp8089) is a research lead,
not verified support on our eventual kernel. Correct board reset/power wiring and
kernel compatibility still need assessment. A supported USB network adapter could
be an alternative later, but none has been tested here.

## Security and maintainability gate

A replacement is not security-ready merely because it boots:

- Establish a supported userspace/browser and a sustainable kernel/driver update path.
- Remove vendor remote-management services from the replacement environment.
- Require authenticated management; do not carry forward open root network ADB.
- Review privileged services, autologin, SSH keys, sudo policy, firewall, and secret storage.
- Understand whether a usable boot trust/verified-boot model is possible on this hardware.
- Keep original eMMC inaccessible/read-only during initial removable-media experiments,
  with actual source/build checks rather than relying on a project description.

The related Linux image documents passwordless sudo, a USB console autologin, and
kernel/package holds for custom modules. It also documents key-only SSH and disabled
root SSH login. These are nuanced defaults, not evidence of an unauthenticated remote
root service; nevertheless they need review against our threat model. Routine
kernel upgrades are explicitly restricted, so its current update model cannot be
assumed to meet this project's maintenance goal.

## Next safe work

1. Extract this unit's board/display/DRAM/PMIC/touch/network configuration from the
   verified private backup, without executing third-party extraction/build scripts.
2. Compare it with the related A33 Linux port and establish which pieces need porting.
3. Prove a mini-USB diagnostic/recovery path if a data cable becomes available; confirm
   the physical removable-card slot and boot route rather than assuming them.
4. Decide whether a board-specific, eMMC-protected SD experiment is justified. Present
   the exact image/build, card target/size, hardware differences, risks, observations,
   and rollback procedure for explicit approval **before** writing a card or booting it.

Do not wipe the existing Android as a first step. A failed or unsupported replacement
would otherwise remove the working diagnostic environment without proving recovery.

## Research limitations

- The postmarketOS A33 tablet page surfaced in search, but direct reading encountered
  an anti-bot page; no hardware support claim was verified from that page.
- The checked vendor repair article and Debian browser-package page could not be
  read successfully. Search snippets or inaccessible pages are not verified firmware
  availability, cable compatibility, or current browser-package support.
- No experimental boot, restore, custom-kernel build, USB enumeration, or SD-card
  write was performed during this assessment.
