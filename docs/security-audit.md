# Interim security and privacy audit

Read-only first pass on 2026-10-20, on the firmware documented in
[the device record](device.md). Identity matched the private physical-backup record.
This is not a penetration test, malware verdict, or proof that no personal data
leaves the frame. Raw package, socket, AppOps, and counter records remain private.

## Status: deferred security backlog

On 2026-10-20 the owner chose to defer hardening while experimenting with mock or
non-sensitive content. The proposed cleanup trials below were not approved or
applied at that point; a later narrow browser-cleanup batch is recorded below.
Package-disable trials and broader hardening remain deferred. This deferral is not
a security clearance or permission to use sensitive
accounts, credentials, or personal dashboard data.

Revisit with the USB/recovery and longer-term firmware work, and before introducing
sensitive data:

- [ ] Prove USB management/recovery and retain a working rollback/escape path.
- [ ] Investigate authenticated or USB-only ADB; do not lock out the sole connection.
- [ ] Review network isolation and an appropriate outbound-access policy.
- [x] Review visible optional browser reporting/search suggestions and close test tabs.
- [ ] Review remaining browser permissions and reversible vendor-package cleanup.
- [ ] Repeat bounded traffic observation, including approved startup/reboot testing.
- [ ] Evaluate a maintained OS/browser for the exact board; root access alone does
  not address the obsolete software or establish privacy.

## Approved browser cleanup (2026-10-20)

The owner subsequently approved only the recommended low-risk browser batch:

- In Firefox Settings → Privacy → Data choices, changed **Crash Reporter** and
  **Firefox Health Report** from checked to unchecked. Revisited and confirmed both
  remained unchecked. Undo is to restore those two checkboxes; originals are also
  recorded privately.
- **Telemetry**, **Mozilla Location Service** sharing, and **Show search suggestions**
  were already unchecked and left unchanged. No separate studies control was found
  in the inspected UI; no unsupported preference edits were attempted.
- Closed the agent-opened Home/public-dashboard tabs and duplicate mock tabs, leaving
  one local mock sample. Restored and visually verified true fullscreen with Frame
  Controls available. Public pages can be reopened; no history/profile data was cleared.
- Safe Browsing/TLS controls, password-saving behavior, Android permissions, Unknown
  sources, package states, saved Home, navigation, network policy, and ADB were not
  changed. No package-disable or removal approval is implied.
- All inspection screenshots and helper sidecars were deleted. Device identity and
  verified-backup match checked before changes; Home/accessibility/package enabled
  states and Unknown sources read back unchanged afterward. Settings were revisited,
  but no process restart or device reboot was performed.
- Firefox counters still increased by about 12 KB received and 4 KB transmitted in
  a brief 30-second follow-up. Different intervals/conditions make this unsuitable
  for a direct before/after rate comparison. Remaining traffic purpose/payload is
  unproven; disabling optional reporting is not an egress block or privacy guarantee.

## Findings

| Priority | Observation | Consequence / limitation |
| --- | --- | --- |
| Critical | Root ADB listens on all IPv4 interfaces on TCP 5555; `ro.adb.secure=0`, `ro.secure=0`, `ro.debuggable=1`. | A reachable network peer can control the frame without an Android authorization prompt. Root already exists; USB is needed to investigate recovery, not initial root access. |
| High | Android 4.4.2, Linux 3.4.39, SELinux permissive, Firefox 68.11.0. | Unsupported software and weak containment. Package cleanup cannot make this a supported, trusted personal-account device. |
| High | Inspected IPv4/IPv6 input and output chains have ACCEPT policies and no restrictive host input/output rules. | No observed device-level egress allowlist. Android accounting/tethering chains are not equivalent to an exfiltration firewall. Router policy was not audited. |
| Medium | ADUPS FOTA 5.26 and Softwinner updater are enabled. ADUPS is running and has Internet, external-storage, phone-state, boot-receiver, and reboot grants. | Worth investigating/reversibly disabling for a dashboard-only role. Grants and package branding do not establish collection or transmission on this unit. |
| Medium | Softwinner logging service and OEM Settings update service are active. | Audit candidates, not proven uploaders. Logger, Settings, VPhoto and other packages share the system UID; blanket UID blocking/revocation risks core services. |
| Medium | Firefox has broad legacy install-time grants and active public HTTPS sockets while the local sample is displayed. | Earlier public tabs remain open. Traffic could include page activity or browser background features; the audit did not establish purpose, payload, or telemetry settings. |
| Lower | Factory/test utilities and unused Google/cloud components remain installed. | Potential attack surface, but names alone are not grounds for deletion. Some test apps are already stopped/not launched. Prioritize containment over cosmetic debloating. |

There were 78 installed packages; VPhoto was the only disabled package. KISS and
Frame Controls remain enabled. The only selected accessibility service is Frame
Controls. No notification-listener selection was recorded. The inspected device
policy dump listed no active administrator components. Third-party-source installs
are enabled in the legacy global setting.

Google backup transport is bound, but `backup_enabled` is `0`; a running/bound
transport is not proof of a backup upload. No personal account inventory, contact
contents, photos, browser history, credentials, or application databases were read.
Frame Controls has no Internet grant; KISS has contacts/phone-related grants but no
Internet grant in the inspected package records. This is not protection against a
separate root compromise.

## Network observation and its limits

- Inspected TCP/UDP tables, process-to-socket links, and four per-UID traffic-counter
  snapshots over 60 seconds. No TLS interception, raw payload capture, DNS lookup
  of observed destinations, packet-capture installation, or test account was used.
- Firefox's Wi-Fi counters increased by about 40 KB received and 22 KB transmitted.
  Root-UID counters also increased during the ADB audit; counters alone do not prove
  every root byte belongs to ADB. No other UID increased in this brief window.
- Established public HTTPS connections belonged to Firefox. Some older sockets
  were in CLOSE_WAIT for media/system processes; that state does not mean an active
  upload. Shared UID alone cannot identify the responsible package.
- Both observed listeners were associated with `adbd`: network TCP 5555 and loopback
  TCP 5037. The loopback listener is not an additional all-interface service.
- The sample HTML makes no network requests itself. That does not prevent the
  browser, another open tab, or the OS from accessing the network.
- This short observation misses delayed, boot-time, scheduled, UDP, or other
  intermittent activity. It does not identify encrypted contents, establish what
  happened before the audit, or certify absence of personal-data transmission.

## Recommended reversible cleanup order

These are proposals, **not applied changes or standing approval**.

1. **Contain at the router first.** Prefer a dedicated isolated device network with
   no access to trusted household clients. Deny the frame's WAN access while using
   the local sample. Internet blocking alone does not protect other LAN clients
   from the frame or prevent their access to root ADB. Guest/client isolation may
   also cut off the Mac and a future local dashboard server; verify topology before
   applying it. DNS-only blocking is not a complete boundary.
2. **Clean up browser network activity.** Close test/public tabs, inspect the exact
   Firefox privacy/data-reporting settings, and disable optional reporting/suggestions
   only after recording original values and the tradeoffs. Preserve security checks;
   do not disable Safe Browsing/TLS verification as a substitute for telemetry control.
   Avoid accounts, saved passwords, personal dashboards, and sensitive site grants.
3. **Trial-disable the two standalone updaters**, one at a time: `com.adups.fota`,
   then `com.softwinner.update`. Keep APKs/data, record exact state, verify behavior
   and rollback, and separately test reboot with owner participation. This suspends
   their update function; it does not prove the firmware is clean or remove other
   update paths. Do not disable the whole Settings package or guess which embedded
   service is responsible for vendor activity.
4. **Review nonessential logger/cloud/test components individually.** Candidates
   include Softwinner logging/copy services, factory tests, Cloud Print, and unused
   Google integrations. Inspect dependencies, shared processes/UIDs, and boot behavior
   before a disable trial. Do not remove APKs or edit `/system`. Do not clear personal
   app data as supposed "recoverable cleanup"; retained backups are private and a
   full restore has not been proven.
5. **Reduce remaining capabilities selectively.** Turn off third-party-source
   installation through its supported control if the owner approves, without
   assuming that toggles ADB authorization. Consider proven package-specific AppOps
   only after inspecting this exact API-19 implementation. Modern runtime permission
   revocation assumptions do not apply, and shared-UID grants are not app-isolated.
6. **Harden ADB only with a proven alternate management path.** Until USB/recovery
   is tested, avoid disabling the sole remote access path or experimenting with boot
   properties. Router containment is the safer immediate boundary. Later evaluate
   authenticated/USB-only management and a maintained replacement OS for this exact
   board; neither is currently validated.

For each approved device change, save the original state privately, state the exact
target/payload/undo, change only one thing, read back, test Settings/Home/browser and
management access, and stop on unexpected changes. The verified backup is necessary
but not proof that firmware restoration works. `pm enable PACKAGE` is a functional
undo for a disable trial; this KitKat CLI lacks the checked `default-state` command,
so do not call it byte-identical restoration of enabled mode `0`.

## Next audit stage

After a separately approved containment/browser-cleanup batch, repeat the idle
observation with only the local sample open. A longer bounded router/device traffic
observation, including an approved reboot, would improve coverage. Connection metadata
can identify unexpected destinations but cannot prove encrypted payload contents.
Do not upload raw captures, unique identifiers, or device-tied addresses to public
scanners. No finite audit guarantees a zero-exfiltration stock firmware; enforce the
required network boundary instead of relying solely on observed quiet periods.
