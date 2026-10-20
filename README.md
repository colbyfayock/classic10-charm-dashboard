# Classic10 Charm Dashboard

Repurposing a Dragon Touch Classic10 Charm running Android 4.4.2 as an open-source family dashboard.

## Project status

This project is under active investigation. The tested frame currently has:

- Allwinner A33-family hardware
- Android 4.4.2 / API 19
- 32-bit ARMv7
- 1280×800 display at 160 dpi
- Approximately 1 GB RAM and 16 GB eMMC
- VPhoto as the stock Home application
- Persistent root ADB over Wi-Fi on TCP 5555

The private backup is now complete and independently verified. Current research
compares an [owner-controlled replacement OS](docs/os-feasibility.md) with a
[reversible interim browser setup](docs/interim-setup.md) adapted from the upstream
Modern10 guide. Frame Controls is installed and physically tested; KISS is installed
with physical launcher tests pending. Firefox remains uninstalled pending its broader
legacy permission decision. No replacement OS has been installed. Stock Android 4.4
is not treated as a secure personal-account browsing environment; VPhoto remains
available as a fallback during reversible testing.

> [!WARNING]
> Network ADB on the tested firmware is root and does not require host authorization. Keep the frame on a trusted or isolated network. Never expose TCP 5555 to the internet.

## Repository layout

- `docs/` — sanitized device findings and setup documentation
- `tools/` — tested host-side utilities that contain no device-specific data
- `dashboard/` — legacy-compatible dashboard source when implementation begins
- `android/` — optional Android 4.4-compatible kiosk source if browser mode is insufficient

## Safety principles

1. Read and identify the exact device before making changes.
2. Never write to the frame before creating and verifying a private backup.
3. Ask before every frame write and record the undo path first.
4. Stop on any model, size, partition, offset, or hash mismatch.
5. Make one change at a time and verify it through readback.
6. Keep a physical route to Android Settings and the stock Home app.
7. Keep firmware dumps, backups, credentials, and unique identifiers private.

See [AGENTS.md](AGENTS.md) for the rules that apply to automated tools and coding agents.

## Host tools

### Localhost ADB relay

Some macOS configurations allow ordinary TCP clients to reach the frame while the ADB daemon reports `No route to host`. `tools/adb_tcp_relay.py` provides a localhost-only relay without exposing another network listener.

```sh
python3 tools/adb_tcp_relay.py FRAME_ADDRESS
adb connect 127.0.0.1:15555
adb -s 127.0.0.1:15555 shell id
```

Run its test with:

```sh
python3 -m unittest discover -s tools -v
```

Do not place a real frame address in source files, documentation, issues, or commits.

For recurring connection failures, see [connection troubleshooting](docs/connection-troubleshooting.md).
It distinguishes host ADB permission failures, offline protocol sessions, and basic
LAN reachability problems; they require different investigations.

For credential-free LAN lookup, see [local device discovery](docs/device-discovery.md).
Nmap and a reusable MAC-profile finder are available on the development Mac:
`python3 tools/find_device.py photo-frame`. No Eero client login or recurring scanner
is configured. Live inventory, identifiers, and network approval remain private.

## Privacy

Enable the repository's pre-commit checks after cloning:

```sh
brew install gitleaks
git config core.hooksPath .githooks
```

The hook scans staged Git blobs for private addresses, device identifiers, sensitive
artifact paths, binary content, and secrets. It fails closed when Gitleaks is missing.
Loopback and reserved documentation addresses are permitted. CI independently runs
the privacy scanner and Gitleaks; configure the `privacy` job as a required branch
protection check. Hooks can be bypassed and CI runs after a push, so neither replaces
reviewing staged files before publishing them. Scanners cannot detect every secret
or unlabeled identifier. Revoke any credential accidentally published.

Run `python3 tools/privacy_check.py --staged` to check the index manually.

Local device backups may be kept in the ignored `backups/` directory with
owner-only permissions. Never force-add backup files, copy their contents into
tracked files, or bypass the privacy hook. This is a local storage convention,
not permission to publish firmware or device data.

Public reports must not contain:

- Serial numbers, MAC addresses, eMMC CIDs, or other unique identifiers
- Private or public IP addresses tied to a device
- Wi-Fi names or passwords
- Tokens, API keys, account IDs, dashboard URLs with credentials, or personal data
- Whole-disk hashes, raw sectors, firmware dumps, backups, or vendor APKs
- Photos showing people, homes, delivery information, or location details

Firmware build strings, Android properties, partition layouts, and hashes of public downloads or non-unique firmware images may be documented when they do not identify an individual unit.

## Related project

This work was inspired by [wesbos/photo-frame-dashboard](https://github.com/wesbos/photo-frame-dashboard), which documents many Android photo frames and the safety practices used here.

## License

[MIT](LICENSE)
