# 02 — Bridge skeleton (Python): MQTT ↔ Supabase

Status: ready-for-agent

## Problem

No bridge service exists. Build the Python Bridge earlier speced in `.scratch/rempah/spec.md` (Implementation Decisions → Bridge).

## Requirements

- MQTT (paho-mqtt) client: subscribes to `rempah/+/telemetry` and `rempah/+/state`, publishes to `rempah/{device_id}/command`.
- Persists telemetry rows to `sensor_logs` and state updates to `device_state`.
- Subscribes to new `commands` rows (supabase-py Realtime; fallback to LISTEN/NOTIFY or polling if unreliable) and dispatches them over MQTT.
- Env-config driven (broker URL, credentials, Supabase URL/keys) and containerisable — deployment-agnostic for the future VPS move.

## Acceptance

- With a stub broker and stub Supabase, telemetry and state messages land in the correct tables.
- A new command row is published on the device's `command` topic.
- Runs from env config with no hardcoded secrets.

Blocked by: 01