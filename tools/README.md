# Host tools

Host-side utilities in this directory must be device-agnostic, avoid embedding private addresses or identifiers, and bind local network services to loopback by default.

## ADB TCP relay

`adb_tcp_relay.py` forwards a localhost port to a frame's ADB port. It exists for macOS environments where ordinary TCP clients can reach the frame but the ADB daemon reports `No route to host`.

```sh
python3 tools/adb_tcp_relay.py FRAME_ADDRESS
adb connect 127.0.0.1:15555
```

The relay accepts a new ADB client after a disconnect or frame reboot. Stop it with `Ctrl-C` when the management session ends.
