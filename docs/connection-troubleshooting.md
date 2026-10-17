# Connection troubleshooting

These notes separate failures observed on the tested Classic10 Charm from reports
about other frames. A similar error message is not proof of the same cause.

## Classify the failure before changing anything

| Observation | What it establishes | Next action |
| --- | --- | --- |
| `nc` reaches TCP 5555, but direct `adb connect` says `No route to host` | The endpoint is reachable from at least one host process; ADB has a host-specific problem | Check the host ADB server and macOS Local Network access; the localhost relay is a tested workaround here |
| TCP connects, but ADB stays `offline` or does not answer CNXN | TCP reachability alone does not establish a usable ADB daemon | Close competing management clients, then make one isolated attempt; do not assume an authorization dialog |
| `Host is down` or timeout, plus an unresolved local ARP/neighbor entry | Basic reachability to the supplied endpoint is not established | Reconfirm the displayed address, router lease, network path, and device connectivity before further ADB commands |
| TCP is refused | Something actively rejected the connection | Investigate port/service state or router rejection; this is not equivalent to a silent unreachable host |

Ping alone is not conclusive: a device may reject ICMP while still accepting TCP.
Likewise, a vendor screen saying Wi-Fi is connected does not prove that the Mac can
reach its displayed address.

## Findings on this unit

- The frame's displayed address changed between sessions. Connecting using the
  owner-confirmed new address restored access on one occasion. Never embed a real
  address in source, examples, issue reports, or public logs.
- A reachable endpoint also once stopped answering the tested ADB handshake.
  Closing our host clients did not resolve that isolated attempt; an owner-performed
  physical restart restored access. This does not establish the original cause.
- A later session again reported `Host is down` and unresolved neighbor lookup,
  despite owner confirmation of the displayed address and regular Wi-Fi network.
  The Mac could reach a local gateway TCP service. That recurring failure remains
  a useful example of why screen/router records need checking against the active
  interface: the owner subsequently found two candidate addresses in Eero, and the
  alternate restored access. See the confirmed result below; the exact reason for
  duplicate Eero records remains unproven.
- Successful root ADB sessions persisted after tested software and physical reboots,
  but this does not guarantee that networking will be reachable after every reboot.
- The frame uses the ESP8089 Wi-Fi driver. No hardware-specific reconnect fix has
  been validated on this Android 4.4.2 firmware.

### Eero duplicate-address investigation

The owner found two candidate IPv4 addresses in Eero. A bounded check reached ADB
at the alternate address. Exact model, firmware, capacities, partition layout, and
the private physical-device fingerprint all matched the verified backup.

Read-only `netcfg` and BusyBox `ip -4 addr show` then confirmed exactly one
non-loopback IPv4 address on the frame: the reachable candidate. The older,
unreachable address was not assigned to an interface in that observation.

This confirms that targeting an address no longer assigned to the frame explained
the latest management failure. It does not establish why Eero retained two entries
or why a previously viewed frame screen appeared to show the old value. Stale lease
history or duplicate client identities are possibilities, not proven causes.

The observed Wi-Fi MAC was not locally administered, but one observation does not
prove stability across boots. A private baseline is available for a future
comparison. Never copy that MAC, either address, or the physical fingerprint into
public notes.

Before adding an Eero DHCP reservation, identify the active entry by comparing its
MAC locally with the frame's current Wi-Fi interface. Different MACs may indicate
distinct client identities; the same MAC with multiple addresses may indicate
lease history. Neither should be assumed without checking. A reservation is a
separate router change requiring approval; it is not applied by these tools.

## Read-only management sequence

1. Obtain the address currently shown on the frame. If a router client list is
   available, compare it with the active lease instead of trusting an old address.
2. Make one bounded port check, substituting the current address locally:

   ```sh
   nc -vz -G 3 FRAME_ADDRESS 5555
   ```

   `-G` is the macOS connection-timeout option. Do not publish raw network output
   containing real addresses or MAC identifiers.
3. If the endpoint is unreachable, inspect the route and neighbor resolution. Check
   whether the Mac can reach the local gateway. Stop ADB-specific retries until
   endpoint reachability is restored. Do not weaken router isolation or firewall
   settings broadly to make a test pass.
4. Once TCP works, use one host ADB server and one relay. Close old direct/relay
   sessions rather than probing the frame with competing ADB clients.
5. Connect through the documented localhost relay and verify exact model, firmware,
   root, and physical identity against the private backup before device operations.
6. Treat physical restarts or Wi-Fi reconnects as specific owner-approved diagnostic
   tests, not a proven permanent fix or an endless retry loop.

### Explicit client disconnect/reconnect

For an offline or stale localhost transport, reset only that client:

```sh
adb disconnect 127.0.0.1:15555
adb connect 127.0.0.1:15555
adb -s 127.0.0.1:15555 get-state
```

The relay closes its downstream socket when the client disconnects and accepts a
new session. During our explicit project pause, ADB was disconnected and the relay
was stopped; an old project session was not intentionally left attached.

On a later failed session, this targeted reset did not restore access: ADB returned
offline, a separate TCP check still reported `Host is down`, and the relay had only
its listener open with no active client connection. Clearing an offline transport
is useful housekeeping but does not resolve missing LAN reachability.

## Next evidence needed for a durable fix

Once access returns, privately compare the frame's Wi-Fi identity and router lease
across boots and reconnects. If its MAC is stable, a router DHCP reservation may
reduce address changes, but it will not fix an independent unreachable-host fault.
Do not assume MAC randomization without observing it, or change network settings
without approval. Device Wi-Fi sleep/power state is another hypothesis to inspect,
not a diagnosed cause.

A legitimate USB data connection is a possible independent management path if the
physical port supports device mode. The `mtp,adb` property alone does not establish
that the data pins are connected. Never use a USB-A-to-A cable or treat a host-only
USB socket as an ADB device port.

## Related upstream reports

- [Skylight macOS Local Network/ADB note](https://github.com/wesbos/photo-frame-dashboard/blob/main/docs/android14-dsu.md):
  `nc` worked while direct ADB failed; restarting its host daemon helped that unit.
- [Joyhong JT101F-I02 ADB behavior](https://github.com/wesbos/photo-frame-dashboard/blob/main/docs/joyhong-jt101f-i02.md#adb-and-root):
  one TCP ADB client at a time; a second host appeared offline. This is related
  hardware, not verification of the same limit on every Classic10 firmware.
- [VESWWE reachability observations](https://github.com/wesbos/photo-frame-dashboard/blob/main/docs/veswwe-10.1.md#confirmed-observations):
  `Host is down` and missing ARP reachability must be resolved before interpreting
  the result as ADB availability. The tested hardware differs from this frame.
- [PF1007L Wi-Fi notes](https://github.com/wesbos/photo-frame-dashboard/blob/main/docs/pf1007l-start-here.md):
  some units have changing Wi-Fi MACs and DHCP addresses. Those reports describe
  different Wi-Fi hardware. Their MAC-pinning or boot-fix scripts are **not validated
  for this ESP8089 Classic10**.
