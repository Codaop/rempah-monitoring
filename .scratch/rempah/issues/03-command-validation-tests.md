# 03 — Command validation (Option B) + emergency-stop bypass + tests

Status: ready-for-agent

## Problem

Commands must never act on stale state. Implement the optimistic-concurrency validation at the Bridge and prove it with the founding test suite from `.scratch/rempah/spec.md` (Implementation Decisions → Command safety; Testing Decisions).

## Requirements

- Compare `expected_current_state` against `device_state`; forward on match, reject (status `rejected`) on mismatch.
- Emergency Stop validates nothing and is always forwarded.
- Respond to `command_failed`/`command_executed` causes in state messages by updating `commands.status` to `failed`/`succeeded`.

## Acceptance

- Test drives the Bridge at its MQTT/Supabase seam with stubs and asserts only observable effects.
- Cases: happy-path forward; mismatch rejection; e-stop bypass with no expectation; command-failed status; telemetry persistence; hybrid alert triggers (device-detected binary events end-to-end, Bridge-computed over-temperature).

Blocked by: 01, 02