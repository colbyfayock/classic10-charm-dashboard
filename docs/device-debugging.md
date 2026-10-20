# Agent device-debugging workflow

Project-specific operating guidance. Read this with [AGENTS.md](../AGENTS.md), the
[device record](device.md), and the current private Obsidian handoff. A global skill
is unnecessary while these instructions are specific to this frame and repository.

## Connect without repeating known failures

1. Locate the private MAC profile with `tools/find_device.py`; do not trust an old IP
   or an offline Eero history entry. Discovery is not Android identity verification.
2. Check TCP reachability once, then use one ADB client/relay. Classify failures with
   [connection troubleshooting](connection-troubleshooting.md), not blind reboots.
3. On the tested Mac, use `/usr/bin/python3` for the TCP relay. After the Nmap install,
   default Homebrew Python 3.15 returned errno 65 for the same endpoint that system
   Python 3.9.6 could reach. No global rollback or privacy setting was needed to use
   the working interpreter. This is an observed workaround, not a universal fix.
4. Verify the exact frame before device operations; retain the backup/readiness
   guards. Read-only diagnosis of a failed readiness condition does not make it
   pass or authorize an installation/flash.

## Inspect the screen directly

- Check the resumed/focused component with `dumpsys activity activities` or the
  focused window with `dumpsys window windows`.
- Capture a screenshot and inspect it with the image-reading tool. Do not ask the
  owner whether a screen is KISS/VPhoto when package state and an image can tell us.
- This daemon does not support `adb exec-out` or `shell -T`. Do not retry these each
  session or stream raw PNG bytes through its PTY.
- The established read-only capture uses BusyBox shell `pipefail`, then
  `/system/bin/screencap -p` piped into BusyBox `hexdump -v` with hexadecimal output.
  Decode the text on the host, require the successful pipeline marker, and verify
  a complete readable PNG before inspection. Do not create a screenshot file on
  the frame. This was tested at 1280×800.
- Treat a screenshot as a momentary UI observation. Cross-check the foreground
  package; inherited wallpaper is not evidence of a different launcher or OS.
- Use targeted logs to distinguish a crash, normal activity navigation, and explicit
  foreground takeover. Do not disable a package/service just because its name or
  process appears near an event. Read-only evidence and approved tests come first.

## Screenshot lifetime: capture → inspect → delete

1. Prefer the fixed ignored, owner-only in-repository path below. It avoids repeated
   external-directory permission prompts. Use a private harness temp directory only
   when the helper is unavailable. Never use tracked source or vault attachments.
2. Capture only the non-sensitive UI needed for the current test. Avoid credential,
   account, personal-photo, or other sensitive screens unless explicitly necessary
   and approved. Never log secrets or typed credentials.
3. Inspect the image, record the relevant finding in the private project log, then
   immediately delete that exact screenshot and any sidecar created for it. Do not
   create a metadata file for every shot unless it serves the current investigation.
4. If interrupted, clean up known captures at the next opportunity and before pause
   or handoff. Use exact paths/ownership evidence, not broad recursive deletion.
   Leave unknown files alone and ask when ownership is unclear.
5. Keep evidence only on explicit owner request. Store the minimum required under
   private ignored storage, note why it is retained, and agree when to remove it.
   Never commit raw device screenshots, logs, or identifiers.

The log should preserve conclusions such as "KISS welcome screen confirmed by PNG
and foreground activity; image deleted," not an accumulating screenshot gallery.

### Reusable capture and cleanup

Run these exact commands from the repository root:

```sh
/usr/bin/python3 tools/frame_screen.py capture
# Inspect backups/screenshots/current.png with the image-reading tool.
/usr/bin/python3 tools/frame_screen.py cleanup
```

The helper uses the existing loopback ADB transport, checks the documented device
identity/storage and API, validates PNG chunk CRCs, and creates no file on the frame.
It checks Git ignores both outputs, refuses to overwrite a pending capture, and
deletes only its hash-matching `current.png` and ownership marker `current.json`.
The marker is minimal cleanup provenance, not a retained screenshot archive.

`opencode.jsonc` allows only these two exact shell commands and reading the fixed
image. It asks before tool edits to the helper, its identity-check dependency, or
the permission file. This is not a shell sandbox: host/global/agent policies still
apply, and more restrictive rules may still prompt. No blanket ADB, external-path,
install, settings, or global permission allowance is added. Config reload behavior
may require reopening the project; do not restart an active device transaction.

## Test and communicate efficiently

- Agree on the batch of changes/tests, permissions, rollback, and approximate time
  before modifying the frame. Do routine guarded steps autonomously inside that scope.
- Use ADB/screenshot inspection for approved UI debugging; request owner input for
  actual touch/hardware confirmation or new consent, not redundant screen guesses.
- Do not label injected input as a physically verified gesture. Do not select a
  permanent default, accept account/site permissions, or disable another component
  outside the agreed scope.
- One hypothesis/change at a time, then check actual state and screen. CLI success
  alone is not a stable foreground, a default selection, or a successful reboot.
- Keep work proportional and timeboxed. Stop for safety mismatches, unexpected
  permission/risk expansion, or material overruns; do not build extra infrastructure
  when a one-off diagnostic is sufficient.
- After completion, state the outcome, unresolved limits, and next step immediately.
  On pause, disconnect ADB/stop only this project's relay and record the real state;
  do not silently revert owner choices or disable on-device services.
