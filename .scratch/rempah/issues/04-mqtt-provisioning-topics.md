# 04 — MQTT provisioning, auth, and topic contract

Status: ready-for-agent

## Problem

Devices and the Bridge need broker credentials, and firmware needs the exact topic and payload contract to implement against.

## Requirements

- Document the HiveMQ Cloud provisioning flow: per-device username/password over TLS (port 8883), separate Bridge credential, Let's Encrypt cert + TLS-SNI firmware support.
- Publish the contract from `.scratch/rempah/spec.md`: topics `rempah/{device_id}/telemetry|state|command`; telemetry payload (5s cadence); retained state payload `{device_id, mode, cause, command_id?, ts}` with causes `command_executed` / `command_failed` / `detected`.
- Provide a contract example/canonical payload file the firmware team can copy from.

## Acceptance

- A provisioning checklist document exists.
- Canonical payload examples match the spec exactly.