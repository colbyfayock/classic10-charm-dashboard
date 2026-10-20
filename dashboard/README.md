# Dashboard sample

Production dashboard development lives in the separate
**[Sabio repository](https://github.com/colbyfayock/sabio)**. This directory stays here
as a self-contained frame/browser compatibility fixture, not the application backend
or a second dashboard implementation.

`sample.html` is a self-contained, mock-only dashboard for checking the layout and
browser behavior on older Android devices. It has no dependencies, network calls,
accounts, or persistent storage. Weather, schedule, and checklist content is generic
sample data; the live clock uses the device's local time.

Open `sample.html` directly in Firefox, or serve this directory from a trusted host
on loopback only, for example:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory dashboard
```

Then visit `http://127.0.0.1:8000/sample.html` on the same host. The fullscreen
control reports the browser's actual fullscreen state and offers an exit action.

## Hardware result (2026-10-20)

On the Classic10 Charm, Firefox Android 68.11.0 rendered this page from a local HTML
file and entered true 1280×800 DOM fullscreen after an ADB-injected button tap.
Tabs/address bar disappeared and the page confirmed its fullscreen state. Exiting
restored browser chrome; a mock checkbox also toggled correctly. The clock updated
between observations. Physical owner touch, long-duration operation, automatic
startup, and reboot persistence were not tested in this cycle.

The tested frame copy is `file:///sdcard/Download/classic10-sample.html`. Deployment
is not automatic: identify the device, verify a private backup, record the exact
target/undo path, and obtain a scoped owner approval before copying or replacing it.
The sample uses a user gesture for fullscreen; it is not an unattended kiosk.
Frame Controls remained visible as an independent Android overlay.

Future dashboard work must avoid unsupported JavaScript/CSS, remain usable at
1280×800, and operate within approximately 1 GB RAM. This compatible sample does not
prove the modern upstream dashboard works; that app's navigation rendered but its
main pane remained blank on this browser. Do not use this obsolete browser/OS for
sensitive accounts.
