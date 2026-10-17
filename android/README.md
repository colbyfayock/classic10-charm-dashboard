# Android components

[Frame Controls](navigation/README.md) is the API 19 Back/Home helper. It is installed
and owner-enabled on the tested unit; Back/Home/Move/Hide-Start physical tests passed.
Its build, privilege boundaries, artifact fingerprints, remaining tests, and
fresh-install approval gate are documented there.

An optional kiosk may be investigated later if a browser-first setup is insufficient.
Any component must preserve a tested route to Android Settings and VPhoto. No
default-Home change is permitted until recovery and undo are proven and approved.
