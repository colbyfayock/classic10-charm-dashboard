# Local device discovery

Nmap is available on the development Mac for credential-free LAN discovery.
Eero client software is **not installed or authenticated**. No Eero password,
verification code, token, or router API session is required for this approach.

## What is currently available

- Nmap 7.992, installed from official Homebrew core with bottle checksum checks.
- Built-in `arp` and `dns-sd` tools.
- Reusable `tools/find_device.py` with private device aliases and approved network binding.
- No `arp-scan`, Fing, or Eero CLI.

The Homebrew installation included its dependencies and upgrades, including
OpenSSL 4 and Python 3.15. It was not a standalone-binary-only host change. No
frame package, router setting, or Wi-Fi credential was changed.

## MAC-first workflow

### Reusable command

From the repository root, as the normal Mac user:

```sh
python3 tools/find_device.py photo-frame --check
python3 tools/find_device.py photo-frame
python3 tools/find_device.py photo-frame --json
```

`--check` validates the private profile, current network, and pinned scanner without
scanning or asking for administrator approval. A normal invocation performs one
fresh, bounded ARP-only lookup. On a unique match it prints only the current IP;
`--json` adds status, observation time, private receipt path, and explicit false
service/physical-identity verification fields. Output contains private addresses;
do not send it to public CI logs or commit it.

Exit codes: `0` unique match/preflight ready, `2` no matching ARP responder,
`3` multiple addresses matched (none selected automatically), `1` configuration,
scope, scan, or permission failure, and `130` caller interruption.

Do not run the Python program with sudo. It asks macOS to elevate only a fixed
network/binary recheck and the pinned Nmap ARP scan. It never receives a password.
The interface address/mask, gateway, cached gateway MAC, and executable digest are
rechecked after that prompt before scan execution. If the caller is interrupted,
an already elevated bounded scan may finish independently; no recurring job or
subsequent scan is scheduled.

### Private profile and approval boundary

Profiles live at `backups/device-profiles/<alias>.json` with mode 0600, under owner-only
0700 directories. The existing `photo-frame` profile was provisioned under the
owner's explicit network/finder approval. No real profile is shipped in Git.

Its `mac` field identifies the NIC to locate. Its `discovery` object records:

- `approved: true`, approved interface, exact private IPv4 subnet, gateway address,
  and gateway MAC from the owner-approved inventory.
- Canonical `nmap_path` and `nmap_sha256` from the reviewed Homebrew installation.

The command never learns/approves an arbitrary current network automatically. It
refuses a different subnet, interface, gateway identity, scanner, public/oversized
scope, symlink, or insufficiently private profile. Scope is capped at 1,024 addresses.
Network-MAC binding is a useful accidental-scan guard, not authentication against
a hostile network that spoofs those values. Review/update private approval only
when the owner authorizes a changed network or tool version.

To add another device, create a new owner-approved private alias profile with its
MAC and the appropriate approved discovery binding. Do not put MACs in command
arguments, public examples, or source. No cloud/router credentials are part of a profile.

Each invocation saves raw XML, private inventory, result, and scope receipt under
`backups/network-discovery/finder-.../`. A successful empty result clears current
candidate addresses rather than returning a stale IP. Failed/cancelled scans do not
report a match; previous records are historical, not proof of current reachability.
Profile checkpoints are replaced atomically and reject a concurrent edit. A lock
prevents overlapping finder invocations while the caller is running.

### Validation evidence

Host tests cover MAC formats, changed scope, tool pin/symlink rejection, malformed
or unsuccessful/out-of-scope/port-scan XML, deduplication, missing/multiple matches,
private profile handling, no-scan preflight, and preservation of concurrent edits.

The first real command preflight passed. Its live ARP scan completed with 26 neighbors
but no frame match, so it returned `not_found`/exit 2; this was not promoted to a
successful current-device match. Replaying the prior successful real ARP capture
through the same parser found the correct single match among its 27 responders.
This tests both outcomes without repeatedly probing a frame that did not respond.

The command does not check ports, authenticate a device, connect ADB, start a relay,
or change the frame. Those remain separate, explicitly approved verification steps.

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

The command and earlier one-time scans install no recurring scan or background
monitoring job. The reusable finder is now available; its profile/approval and
validation evidence are described above. For basic MAC-to-IP lookup this local
approach has worked, so Eero authentication is not needed merely to find the frame.

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
