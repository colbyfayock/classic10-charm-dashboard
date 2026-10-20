#!/usr/bin/env python3
"""Find a private MAC profile on its approved macOS LAN. Never contacts ADB/Eero."""

import argparse
import datetime
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shlex
import stat
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MAX_ADDRESSES = 1024

# Recheck after the native administrator prompt, not only before it appears.
# Only the pinned scanner is executed with elevation; no Python or device code.
ADMIN_GUARD = r'''
set -eu
[ "$(/usr/sbin/ipconfig getifaddr "$1")" = "$2" ] || exit 77
[ "$(/usr/sbin/ipconfig getoption "$1" subnet_mask)" = "$3" ] || exit 77
[ "$(/usr/sbin/ipconfig getoption "$1" router)" = "$4" ] || exit 77
current_mac=$(/usr/sbin/arp -n "$4" | /usr/bin/awk -v iface="$1" '{ mac=""; ok=0; for(i=1;i<=NF;i++){if($i=="at")mac=$(i+1);if($i=="on" && $(i+1)==iface)ok=1;}if(ok)print tolower(mac);}')
[ "$current_mac" = "$5" ] || exit 77
current_hash=$(/usr/bin/openssl dgst -sha256 "$6" | /usr/bin/awk '{print $NF}')
[ "$current_hash" = "$7" ] || exit 78
exec "$6" --privileged -sn -PR --send-eth -n -e "$1" --max-retries 1 --max-rate 40 --max-parallelism 32 --host-timeout 10s -oX - "$8"
'''


def normalize_mac(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{1,2}(?:[:-][0-9a-fA-F]{1,2}){5}", value):
        raise ValueError("Invalid MAC format in private configuration/output")
    parts = [int(part, 16) for part in re.split("[:-]", value)]
    if parts[0] & 1 or not any(parts):
        raise ValueError("MAC must identify a nonzero unicast interface")
    return ":".join(f"{part:02x}" for part in parts)


def private_directory(path):
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Private directory is missing or symlinked")
    if stat.S_IMODE(path.stat().st_mode) != 0o700 or path.stat().st_uid != os.getuid():
        raise ValueError("Private directories must be owner-only and owned by this user")


def load_profile(root, alias):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", alias):
        raise ValueError("Device alias must be a simple lowercase name")
    folder = root / "backups/device-profiles"
    private_directory(root / "backups")
    private_directory(folder)
    path = folder / (alias + ".json")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Private device profile is missing or symlinked")
    if stat.S_IMODE(path.stat().st_mode) != 0o600 or path.stat().st_uid != os.getuid() or path.stat().st_size > 65536:
        raise ValueError("Profile must be a bounded owner-only file")
    original = path.read_bytes()
    profile = json.loads(original)
    if not isinstance(profile, dict):
        raise ValueError("Invalid private profile object")
    profile["mac"] = normalize_mac(profile.get("mac"))
    if not isinstance(profile.get("discovery"), dict):
        raise ValueError("Private discovery approval is not configured; do not infer it from current Wi-Fi")
    return path, profile, original


def read_command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError("Could not read current interface/gateway state")
    return result.stdout.strip()


def current_network(interface):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,15}", interface):
        raise ValueError("Invalid configured interface")
    address = str(ipaddress.IPv4Address(read_command(["/usr/sbin/ipconfig", "getifaddr", interface])))
    mask = read_command(["/usr/sbin/ipconfig", "getoption", interface, "subnet_mask"])
    gateway = str(ipaddress.IPv4Address(read_command(["/usr/sbin/ipconfig", "getoption", interface, "router"])))
    arp = read_command(["/usr/sbin/arp", "-n", gateway])
    matches = re.findall(r"\bat\s+([0-9a-fA-F]{1,2}(?:[:][0-9a-fA-F]{1,2}){5})\b.* on " + re.escape(interface) + r"(?:\s|$)", arp)
    if len(set(matches)) != 1:
        raise ValueError("Gateway neighbor identity is unavailable/ambiguous; no scan allowed")
    raw_mac = matches[0].lower()
    return {"interface": interface, "address": address, "netmask": mask,
            "network": str(ipaddress.ip_network(address + "/" + mask, strict=False)),
            "gateway": gateway, "gateway_mac": normalize_mac(raw_mac), "gateway_raw_mac": raw_mac}


def validate_binding(binding, observed):
    if binding.get("approved") is not True:
        raise ValueError("This private network scope is not approved")
    network = ipaddress.ip_network(binding["network"], strict=True)
    if (network.version != 4 or not network.is_private or network.is_loopback
            or network.is_link_local or network.is_multicast or network.network_address.is_unspecified
            or network.num_addresses > MAX_ADDRESSES):
        raise ValueError("Discovery requires a bounded approved private IPv4 subnet")
    actual = ipaddress.ip_network(observed["address"] + "/" + observed["netmask"], strict=False)
    if (str(network) != observed["network"] or actual != network
            or binding["interface"] != observed["interface"]
            or str(ipaddress.IPv4Address(binding["gateway"])) != observed["gateway"]
            or normalize_mac(binding["gateway_mac"]) != normalize_mac(observed["gateway_mac"])
            or ipaddress.ip_address(observed["gateway"]) not in network):
        raise ValueError("Network identity differs from private approval; no scan allowed")
    return network


def verify_binary(path, expected):
    path = Path(path)
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
            or not os.access(path, os.X_OK) or not re.fullmatch(r"[0-9a-f]{64}", expected)):
        raise ValueError("Pinned Nmap executable is missing, symlinked, or invalid")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Nmap differs from the reviewed private pin; no elevation allowed")


def build_admin_script(observed, binary, digest):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,15}", observed["interface"]):
        raise ValueError("Invalid interface")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or not Path(binary).is_absolute():
        raise ValueError("Invalid executable pin")
    for key in ("address", "netmask", "gateway"):
        ipaddress.IPv4Address(observed[key])
    network = str(ipaddress.IPv4Network(observed["network"], strict=True))
    raw_mac = observed.get("gateway_raw_mac", observed["gateway_mac"]).lower()
    normalize_mac(raw_mac)
    arguments = ["/bin/sh", "-c", ADMIN_GUARD, "device-discovery", observed["interface"],
                 observed["address"], observed["netmask"], observed["gateway"], raw_mac,
                 str(binary), digest, network]
    return "do shell script " + json.dumps(shlex.join(arguments)) + " with administrator privileges"


def parse_scan(xml, network, target_mac):
    if len(xml) > 10 * 1024 * 1024 or "<!ENTITY" in xml.upper():
        raise ValueError("Unexpected or oversized scanner XML")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ValueError("Malformed scanner output; no match accepted") from error
    finished = root.find("runstats/finished")
    if (root.tag != "nmaprun" or root.get("scanner") != "nmap" or finished is None
            or finished.get("exit") != "success" or root.find("scaninfo") is not None
            or root.find(".//port") is not None or root.find(".//script") is not None):
        raise ValueError("Output is not a successful ARP-only discovery")
    scope = ipaddress.IPv4Network(network, strict=True)
    target = normalize_mac(target_mac)
    rows = {}
    for host in root.findall("host"):
        status = host.find("status")
        if status is None or status.get("state") != "up":
            continue
        addresses = {item.get("addrtype"): item.get("addr") for item in host.findall("address")}
        if "ipv4" not in addresses or "mac" not in addresses:
            continue
        address = ipaddress.IPv4Address(addresses["ipv4"])
        if address not in scope or status.get("reason") != "arp-response":
            raise ValueError("Unexpected host scope or non-ARP response")
        mac = normalize_mac(addresses["mac"])
        rows[(str(address), mac)] = {"ipv4": str(address), "mac": mac, "matches_device": mac == target}
    inventory = sorted(rows.values(), key=lambda row: (int(ipaddress.IPv4Address(row["ipv4"])), row["mac"]))
    matches = sorted({row["ipv4"] for row in inventory if row["matches_device"]}, key=ipaddress.IPv4Address)
    return inventory, matches


def save_profile(path, profile, original):
    if path.is_symlink() or path.read_bytes() != original:
        raise ValueError("Profile changed during discovery; refusing to overwrite it")
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(profile, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", help="Alias of an existing approved private MAC profile")
    parser.add_argument("--check", action="store_true", help="Validate profile/network/tool only; do not scan")
    parser.add_argument("--json", action="store_true", help="Machine-readable match result; contains private IPs")
    args = parser.parse_args()
    if platform.system() != "Darwin" or os.geteuid() == 0:
        raise ValueError("Run as your normal macOS user; elevation is limited to Nmap")
    os.umask(0o077)
    path, profile, original = load_profile(ROOT, args.device)
    binding = profile["discovery"]
    observed = current_network(binding["interface"])
    network = validate_binding(binding, observed)
    verify_binary(binding["nmap_path"], binding["nmap_sha256"])
    if args.check:
        payload = {"device": args.device, "status": "ready", "scan_performed": False}
        print(json.dumps(payload) if args.json else "Private profile, current network, and pinned Nmap match. No scan performed.")
        return 0
    output_base = ROOT / "backups/network-discovery"
    if not output_base.exists():
        output_base.mkdir(mode=0o700)
    private_directory(output_base)
    lock_path = output_base / ".finder.lock"
    if lock_path.is_symlink():
        raise ValueError("Refusing symlinked finder lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another finder invocation is still running") from error
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder = output_base / ("finder-" + stamp + "-" + uuid.uuid4().hex[:6])
        folder.mkdir(mode=0o700)
        (folder / "scope.json").write_text(json.dumps(binding, indent=2) + "\n")
        print("ARP-only lookup requested; macOS may ask for local administrator approval.", file=sys.stderr)
        result = subprocess.run(["/usr/bin/osascript", "-e", build_admin_script(observed, binding["nmap_path"], binding["nmap_sha256"])],
                                capture_output=True, text=True, timeout=240)
        (folder / "stderr.txt").write_text(result.stderr)
        (folder / "scan.xml").write_text(result.stdout)
        if result.returncode:
            raise ValueError("Discovery cancelled/failed or post-prompt scope changed; see private receipt")
        inventory, matches = parse_scan(result.stdout, str(network), profile["mac"])
        observed_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = {"device": args.device, "status": "found" if len(matches) == 1 else "ambiguous" if matches else "not_found",
                   "addresses": matches, "observed_utc": observed_utc,
                   "service_verified": False, "physical_identity_verified": False,
                   "receipt": str(folder.relative_to(ROOT))}
        (folder / "devices.json").write_text(json.dumps(inventory, indent=2) + "\n")
        (folder / "result.json").write_text(json.dumps(payload, indent=2) + "\n")
        profile["candidate_addresses"] = [{"ipv4": value, "interface": observed["interface"],
                                            "source": "active_ARP_response", "adb_verified": False,
                                            "physical_identity_verified": False} for value in matches]
        profile["observed_utc"] = observed_utc
        save_profile(path, profile, original)
    if args.json:
        print(json.dumps(payload))
    elif len(matches) == 1:
        print(matches[0])
    else:
        print("No unique MAC match; review the private receipt. No address selected.", file=sys.stderr)
    return 0 if len(matches) == 1 else 3 if matches else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Finder interrupted; no further scan or device operation requested.", file=sys.stderr)
        sys.exit(130)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, ValueError) else type(error).__name__
        print("Finder stopped: " + message, file=sys.stderr)
        sys.exit(1)
