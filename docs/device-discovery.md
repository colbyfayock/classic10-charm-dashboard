# Local device discovery

Nmap is available on the development Mac for credential-free LAN discovery.
Eero client software is **not installed or authenticated**. No Eero password,
verification code, token, or router API session is required for this approach.

## What is currently available

- Nmap 7.992, installed from official Homebrew core with bottle checksum checks.
- Built-in `arp` and `dns-sd` tools.
- No `arp-scan`, Fing, Eero CLI, or custom automated device-finder implementation.

The Homebrew installation included its dependencies and upgrades, including
OpenSSL 4 and Python 3.15. It was not a standalone-binary-only host change. No
frame package, router setting, or Wi-Fi credential was changed.

## MAC-first workflow

For finding a known device, start with local MAC/IP discovery, not a service-port
filter:

1. Run an explicitly approved ARP-only discovery pass on the owner's current LAN.
2. Match its responses against the owner-provided MAC in private configuration.
3. Return the candidate's current IP, keeping actual inventory out of tracked files.
4. Separately check the required service and frame identity before device actions.

On 2026-10-20, an owner-approved ARP-only pass found 27 devices with IPv4/MAC
responses and exactly one match for the owner-supplied frame MAC. That MAC also
matched the privately saved frame Wi-Fi baseline. The pass finished in approximately
63 seconds including local administrator approval. No port scan, ADB command, Eero
API call, or router/frame write was performed by this discovery step.

The private profile is `backups/device-profiles/photo-frame.json`; raw scan and
match records are in ignored `backups/network-discovery/`. No actual MAC, address,
or subnet value is included here. This proves a useful locator, not cryptographic
authentication or that Android ADB is currently usable.

Raw ARP discovery needs local administrator/BPF access on this Mac. Approval was
handled by a native OS prompt; no administrator password was supplied in chat,
source, or command arguments. Sleeping/offline/isolated devices may still be missed,
and discovery does not cross arbitrary routed or guest segments.

## Earlier port-only test and limitations

The owner approved a bounded, unprivileged TCP-connect check of port 5555 only on
their current Eero IPv4 subnet. It used no DNS lookup, service-version detection,
OS fingerprinting, NSE/vulnerability scripts, ADB handshake, or router credentials.

The scan finished in approximately 26 seconds and found zero open TCP-5555
candidates. This means **no reachable candidate was detected at that time**, not
that the LAN had no devices or the frame was necessarily powered off.

A separate positive control correctly detected a temporary loopback-only listener;
that listener was closed afterward. It did not scan any additional LAN endpoint.

This initial ADB-oriented check is not a complete network inventory. Sleeping,
filtered, offline, IPv6-only, guest/isolated, or non-ADB devices may not appear.
With `-Pn`, Nmap assumes host status for scanning: never interpret its host-up count
as confirmed devices. Count only actual open-port results for this candidate mode.
Port 5555's service-database label is not proof that the endpoint speaks Android ADB.

## Safe workflow

1. Confirm the Mac is on the owner's intended network, not public/work Wi-Fi.
2. Derive and review the current subnet; bind approval to that exact scope and
   refuse automatic scanning after a network change.
3. Choose the discovery mode explicitly: an ADB-port candidate check and a general
   host-discovery scan are different operations. Privileged ARP discovery requires
   a separate local-admin decision; never request that password in chat/source.
4. Store XML, normal output, candidate addresses/MACs, and scan metadata only in
   owner-only ignored storage, such as `backups/network-discovery/`.
5. Privately compare candidates with recorded device information. A MAC/name/port
   match is a candidate, not authentication or proof of firmware trust.
6. Before any frame operation, use the existing exact model/firmware/storage/private
   identity checks. Identifier comparison over unauthenticated ADB is not secure
   boot attestation and does not justify automatic writes.

The one-time scans have completed; no recurring scan or background monitoring job
was installed. A tested reusable finder command with explicit network scope and
private configuration is potential next work, not an existing feature. For basic
MAC-to-IP lookup this local approach has now worked, so Eero authentication is not
needed merely to find the frame.

## Eero integration as a later option

An owned, narrow inventory wrapper may be preferable to a full unofficial
router-management CLI if local discovery is insufficient. However, a local command
would still generally call Eero's undocumented cloud API; it would not create a
supported local-only router API or a server-enforced read-only token.

Before that option, review exact source/dependencies/authentication, require
owner-local login, use Keychain storage, allowlist read operations, and keep raw
network/account output private. Do not trust a README's security claims as an audit,
store credentials in this public project, enable blanket force flags, or implement
router writes as part of device lookup.

The [Eero device information documentation](https://eero.com/support/articles/217125606-What-device-information-can-I-see-with-eero)
and [Devices tab documentation](https://eero.com/support/articles/360036022532-What-is-the-Devices-tab-in-the-eero-App)
describe the app's active/recent device inventory. Recently-online records should
not be treated as current reachability. Eero integration remains unapproved for
installation/authentication after the owner's Nmap-first security decision.
