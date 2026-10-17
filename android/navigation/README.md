# Frame Controls (API 19)

An original, small navigation helper for the Classic10 Charm's stock Android 4.4.2.
It provides floating **Back**, **Home**, **Move**, and **Hide** controls after explicit
local opt-in and manual accessibility-service enablement.

**Status:** installed from the inspected artifact and manually enabled by the owner.
Physical Back, Home, Move, and Hide/Start tests passed on this unit. Reboot persistence
and full service revocation/uninstall remain untested. The helper does not upgrade
or secure the obsolete underlying OS.

## Privilege boundaries

- Minimum and target API 19; compiled against the actual API 19 SDK.
- Declares only `SYSTEM_ALERT_WINDOW` as a requested manifest permission.
- Accessibility service is protected by Android's `BIND_ACCESSIBILITY_SERVICE` and
  must be enabled manually by the owner.
- No window-content capability and no accessibility-event subscription. The event
  callback is empty; service event/flag masks are explicitly zero.
- No Internet, contacts, phone, root, or secure-settings permission or commands.
- No Home category, boot receiver, automatic permission enabling, default-app change,
  or vendor-package modification.
- Controls default to off. **Stop controls** or **Hide** removes the overlay; it
  does not revoke Android's accessibility-service selection. Disable the service
  manually in Android Accessibility settings to revoke access completely.

Android's accessibility warning may describe broader privileges than this service
requests/uses. Source and packaged-configuration checks limit this implementation,
but the owner must still explicitly approve the service and later updates.

## Host-only build

Requirements: macOS, JDK 17, Python 3, and Rosetta if needed for Google's x86_64 SDK
tools. SDK licenses and upstream components retain their own terms. The build does
not install global packages, run a frame command, or contact ADB.

From the repository root:

```sh
python3 -m unittest discover -s tools -v
python3 tools/build_navigation_helper.py
```

The script uses ignored, owner-only storage:

- `backups/android-toolchain-downloads/` — pinned official Google SDK archives.
- `backups/android-sdk/` — verified platform and build tools.
- `backups/navigation-signing/` — local private signing key and passphrase.
- `backups/navigation-builds/<build>/` — APK and inspection reports.

It verifies archive size, SHA-1, and SHA-256 before extraction/execution, rejects
unsafe archive paths/symlinks, and checks existing extracted contents against the
pinned archives rather than overwriting mismatches. Build directories are new on
every run. No failed output or private signing material is silently deleted.

The exact legacy SDK bootstrap was explicitly approved by the owner: Google
publishes size/SHA-1 for these archive URLs, so the initial download was verified
against that metadata before SHA-256 pins were recorded in `toolchain.json`.
Those SHA-256 values are not claimed as independently publisher-published digests.
Subsequent runs require every recorded pin. This narrow exception does not apply
to arbitrary downloads, APKs, or firmware.

The pipeline links resources against API 19, compiles Java against its bootclasspath,
uses D8 with minimum API 19, zip-aligns, signs, then verifies v1 signing specifically
for API 19. It also inspects the actual APK's package, SDK declarations, permission
list, manifest, and accessibility configuration.

Keep the private signing files for later updates. Different keys produce different
certificates and cannot silently replace an installed app signed by the old key.
Do not delete keys to bypass an update/signature error. Keys and passphrases are
never committed or placed on the frame by the build script.

## Locally inspected artifact, 2026-10-17

| Field | Value |
| --- | --- |
| Package | `com.colbyfayock.framecontrols` |
| Version / code | 0.1.0 / 1 |
| APK size | 25,055 bytes |
| Minimum / target API | 19 / 19 |
| APK SHA-256 | `a72fbfc7df575b0bcb04eef548fcb84820db5d301528bad1a1875d0177e6b6f7` |
| Signing certificate SHA-256 | `91785fc2368daf0e34d50bb1ed64bb88f2ddf056b21199bef5673a03538d3fd1` |
| API 19 v1 signature verification | Passed |
| Installed and owner-enabled | Yes, on the tested frame |
| Physical controls confirmed | Back, Home, Move, Hide/Start |

The local artifact is in
`backups/navigation-builds/20261017T184011Z-e68e10/frame-controls.apk`.
These are software artifact/certificate fingerprints, not frame identifiers.
Another machine's local signing key or a rebuild may produce a different APK hash;
inspect that exact artifact before approving its installation.

## Tests and limits

Host tests execute the actual Java policy class for opt-in/binding, bounds/clamping,
drag threshold, invalid movement, and rotation-sized bounds. Static tests check
manifest privileges, absence of Home/boot registration, and the accessibility privacy
contract. SDK extraction tests cover pins, traversal, symlinks, and preservation of
existing mismatched files. The full host suite currently has 37 passing tests.

The owner confirmed the visible overlay, Home to VPhoto, dragging, Hide followed by
Start, and Back from Display settings to VPhoto. Preferred/Home records and existing
VPhoto/Settings/SystemUI enabled states remained unchanged. The initial ambiguous
Back response was not counted until the distinct Display-page test passed.

The first install failed with `INSTALL_FAILED_INVALID_URI`: KitKat's separate
default-container UID could not read the group-restricted staging path. Giving
read/traverse access to the temporary non-secret APK path allowed installation;
installed bytes matched the approved hash and staging was removed. No system
security setting was changed to bypass the error.

The first Start interaction returned to VPhoto for an unproven reason. Its opt-in
preference was saved and no helper crash was seen in the reviewed log. Opening
Android Accessibility directly and manually enabling the service worked; the later
Hide/Start cycle also worked. Do not infer a firmware lifecycle fix from this.

Vendor lifecycle behavior, rotation, keyboard interaction, recovery after reboot,
and full accessibility revocation/uninstall still need tests. There is no automatic
secure-settings repair if the vendor disables the service.

## Future installation/test gate

Do not run an installation as part of building. Before an exact install approval:

1. Reconfirm the frame identity against the verified private backup.
2. Recheck the APK hash/signature and whether that package is already installed.
3. Save fresh package/default state privately and disclose overlay/accessibility use.
4. Obtain approval to install this exact APK. Installation alone must not enable
   the service or change Home.
5. Separately approve launching the helper, tapping Start controls, and manually
   enabling it through Android Accessibility settings. Keep ADB available.
6. Physically test Back/Home from Settings, Move, Hide/Stop, VPhoto fallback, and
   service disablement. Be ready to use the proven ADB VPhoto fallback if it fails.
7. Only after physical recovery is proven, propose the launcher/browser installs.

When later approved, disabling the accessibility service and uninstalling
`com.colbyfayock.framecontrols` removes the helper and its local settings. Neither
operation restores firmware or changes VPhoto's system APK. Do not remove the only
working navigation path while a test screen is open; keep the ADB fallback ready.
