# Proposed reversible interim browser setup

Research date: 2026-10-17. **Frame Controls is installed, owner-enabled, and physically
tested. KISS is installed with physical testing pending. Firefox is not installed.**
The owner approved a reversible interim setup while waiting for a mini-USB cable.
Change/test scopes may be batched with explicit permissions, rollback, and time
estimates; unexpected material permission changes still require review.

Long-term goal: [owner-controlled replacement OS](os-feasibility.md). This interim
setup does not make Android 4.4 security-supported, and it does not justify signing
into primary email, banking, administrator accounts, or other sensitive services.

## Adapt the Modern10 guide

Use the same sequence: verified private backup, usable navigation, general launcher,
browser with its own rendering engine, and stock VPhoto fallback. The main change
is choosing components that actually support this unit's API 19.

Prerequisites already verified:

- Complete private chunked capture, including independent stable-range comparisons.
- Root ADB and exact physical identity matching the backup.
- Android Settings visible on the physical panel.
- Explicit VPhoto launch returns to the stock photo app.
- Home resolves to VPhoto and preferred/enabled states remained unchanged in testing.

The stock firmware lacked obvious physical/on-screen Back/Home controls in Settings.
The approved helper now supplies owner-confirmed Back/Home escape, Move, and
Hide/Start. Reboot persistence remains untested. Do not infer a physical escape path
solely from ADB, source, or build checks.

## Candidate 1: minimal API 19 navigation helper

Recommendation: build an original, small helper with floating **Back** and **Home**
controls. This reuses the upstream recovery concept, not its newer-Android binary.

The source implementation and host build are now available in
[`android/navigation/`](../android/navigation/README.md). The constraints below are
implemented/inspected on the host; basic navigation also passed owner physical tests:

- Minimum API 19; compile-time and runtime checks against that minimum.
- Legacy overlay window support, not API 26 `TYPE_APPLICATION_OVERLAY` or notification
  channel APIs. Android's global accessibility Back/Home actions predate API 19.
- Request only the legacy overlay permission and an explicitly enabled accessibility
  service needed for navigation. No Internet, contacts, phone, root, or secure-settings
  permission. Do not read screen contents or record accessibility events.
- Visible enable/disable control; no automatic enabling of accessibility, package
  whitelists, default Home, or boot configuration.
- Keep control placement out of the way of confirmation dialogs and provide an
  obvious way to stop it. Test Back, Home, Settings, drag positioning, and disable.
- Test lifecycle/reboot behavior with owner participation; do not assume persistence.

The upstream `scripts/home-button/` service uses notification channels and modern
application overlays. Its build targets API 26+ and verifies for API 27. The upstream
Home HQ kiosk requires API 23. Neither is a direct API 19 install candidate.

The host build compiled against the actual API 19 platform and passed v1 signature,
SDK, permission, and packaged-accessibility inspection. The exact APK/hash and
private-key handling are documented in its README. Runtime Back/Home, overlay,
dragging, and Hide/Start passed after owner-manual service enablement. Reboot
persistence and full service revocation/uninstall remain untested.

## Candidate 2: KISS Launcher 3.24.2

Preferred researched third-party launcher candidate:

| Field | Official-source metadata |
| --- | --- |
| Package | `fr.neamar.kiss` |
| Version / code | 3.24.2 / 219 |
| Minimum / target API | 15 / 35 |
| APK | `https://f-droid.org/repo/fr.neamar.kiss_219.apk` |
| APK size | 1,206,394 bytes |
| APK SHA-256 | `9f09fe5cc43241906db12763ccf8da35b4430c69e066d20273e2ee41ce891e1e` |
| F-Droid signing certificate SHA-256 | `ec038e5b12c9fb8df23b5ecc1f71dd251bc503b30cec8d58a00cfae2c31abf1b` |
| Source tag | `v3.24.2`, commit `a4ee98551e7b914fa1d042fcdf930eadc587aca6` |

Evidence:

- [F-Droid package page](https://f-droid.org/en/packages/fr.neamar.kiss/) identifies
  this release as requiring Android 4.0.3 or newer.
- The official F-Droid `index-v2.json` record provides the APK size/hash, SDK levels,
  and signing-certificate fingerprint above. The downloaded public index matched
  the size and SHA-256 in the official `entry.json`.
- [Source build config](https://github.com/Neamar/KISS/blob/a4ee98551e7b914fa1d042fcdf930eadc587aca6/app/build.gradle)
  independently declares minSdkVersion 15. Current newer releases require API 21;
  do not substitute a latest APK.

Permission tradeoff: the reviewed manifest/index requests contacts, phone calling,
and phone-state permissions, plus status-bar/package visibility functions. It does
not request Internet access in the reviewed record. **KitKat predates normal
per-permission runtime denial**, so do not promise the contacts/phone permissions
can simply be declined after installation. Disclose this before asking for approval.
Avoid importing contacts/accounts; no personal-data inspection has been performed.

The actual APK matched the pinned bytes, API 15 metadata, valid API-19 v1 signature,
and expected F-Droid certificate/permissions before the approved installation.
Installed bytes match. Explicit launch of `fr.neamar.kiss/.MainActivity` reported
success, but a subsequent focus check found VPhoto foreground again. The cause is
not established; no fatal KISS crash was seen in the reviewed log. Navigation and
preferred/Home records stayed unchanged. Physical UI/chooser testing is pending;
no permanent Home was selected. Repository signing-chain verification is distinct
from the checked exact artifact and certificate pins.

OpenLauncher was considered: its source has API 17 support, but its maintainers
explicitly mark the project discontinued. It is not preferred simply because it
looks more like a traditional desktop.

## Candidate 3: official Firefox 68.11.0 ARM

| Field | Official-source metadata |
| --- | --- |
| Version | 68.11.0 |
| Archive variant | `android-api-16`, Android ARM |
| APK | `https://archive.mozilla.org/pub/mobile/releases/68.11.0/android-api-16/en-US/fennec-68.11.0.en-US.android-arm.apk` |
| APK SHA-256 | `b30c7aa24919eb36a82a742cfc488eab745b607ede0be49ab20060cc9bab96cc` |

Mozilla's [archive checksum manifest](https://archive.mozilla.org/pub/mobile/releases/68.11.0/SHA256SUMS)
provides that hash. The official [release notes](https://www.firefox.com/en-US/firefox/android/68.11.0/releasenotes/)
say this is the final old-Android release and **will receive no further security
updates or bug fixes**. This is a 2020 browser, not the Modern10 guide's Firefox build.

Its independent Gecko engine avoids depending on the stock integrated WebView, but
modern sites may still fail due to unsupported JavaScript, TLS/certificate changes,
or performance. Compatibility has not been tested on this unit. Test only a local
static page and non-sensitive public sites initially. No Firefox account login,
saved credentials, sensitive tokens, or personal-account sessions should be used.

The actual APK matched the official hash, declares API 16 minimum, contains ARMv7
libraries, and verifies v1 signing for API 19. Inspected signing-certificate SHA-256:
`a78b62a5165b4494b2fead9e76a280d22d937fee6251aece599446b2ea319b04`.
Its `.App` launcher alias targets `org.mozilla.gecko.LauncherActivity`; this was read
from the artifact, not assumed from the newer guide.

**Installation is held for a material permission decision.** The actual manifest
also requests account/authentication/sync access, system-settings writes, Wi-Fi
changes, location, external storage, overlay, camera, and microphone capabilities.
Some permissions are normal/signature-only/unknown on this old OS, but KitKat lacks
normal modern runtime denial for its dangerous permissions. These broad legacy
capabilities were not fully disclosed in the initial batch approval. Do not silently
install it while the owner is away or describe the official artifact as malware.

## Approval and test sequence

1. **Host-only build approval:** prepare the minimal navigation helper and verify its
   source, permission scope, API 19 compatibility, signature, and actual APK hash.
2. **Exact helper install approval:** install only that verified artifact, then
   separately approve/enable its accessibility service. Keep ADB/VPhoto fallback.
3. Physically prove Back/Home escape from Settings, verify disabling the helper, and
   record rollback. Do not continue if this fails.
4. **Exact launcher install approval:** disclose KISS permissions, verify the pinned
   artifact, and install without disabling VPhoto. During initial testing select
   **Just once**, not **Always**, if a chooser appears.
5. **Exact browser install approval:** verify the Mozilla artifact and install it;
   launch through the actual declared activity or the tested launcher.
6. Test rendering, touch keyboard, landscape layout, links, download dialogs, TLS,
   Wi-Fi interruption, and physical exit on harmless pages. Do not bypass TLS errors
   or modify system certificate stores as a shortcut.
7. Save post-test package/default state privately and compare with baseline. Default
   Home, startup behavior, updater disablement, or network hardening are separate
   proposed changes, not side effects authorized by these install approvals.

## Undo strategy

- The proven runtime fallback is:

  ```sh
  adb -s 127.0.0.1:15555 shell am start -n com.waophoto.smartframe/.ui.SplashActivity
  ```

- Keep VPhoto installed and enabled throughout testing.
- Disable the new accessibility service before uninstalling its helper. Do not
  assume the helper's future package/component name before it is built.
- With specific approval, uninstall newly added Firefox (`org.mozilla.firefox`) or
  KISS (`fr.neamar.kiss`) if testing fails. Uninstalling deletes their new local app
  data; it is not a firmware rollback.
- If a default Home is later changed, first document and physically test the path
  back to VPhoto before making that separate change. Do not restore a complete
  package-restrictions XML blindly over a running system.
- The full private backup remains available, but a firmware restore path has not
  been proven and is not needed for routine removal of a newly installed test app.

## Current decision gate

The helper's initial physical navigation gate passed. KISS is installed and ready
for owner-present UI/Just-once chooser tests; it is not yet a proven stable launcher
on this vendor firmware. Firefox's artifact checks passed but installation is held
for the broader permission decision. No sensitive login, permanent Home, vendor
disablement, system edit, or replacement-OS change is approved by these trial steps.
