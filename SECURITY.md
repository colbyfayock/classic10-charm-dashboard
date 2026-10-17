# Security policy

## Supported versions

This project is experimental and does not currently publish supported releases.

## Reporting a vulnerability

Do not open a public issue containing credentials, unique device identifiers, private network details, firmware dumps, or personal dashboard data. Use GitHub's private vulnerability reporting feature when available.

Include only the minimum sanitized information needed to explain the problem. Do not attach vendor APKs, raw sectors, whole-disk hashes, or backups.

## Device warning

The tested firmware exposes an unauthenticated root ADB service on TCP 5555. Anyone who can reach that port can control the frame. Keep the device on a trusted or isolated network and do not forward the port from a router or expose it through a public tunnel.
