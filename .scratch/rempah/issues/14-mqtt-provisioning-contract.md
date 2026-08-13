# 14 — MQTT provisioning + canonical contract

**What to build:** A provisioning checklist and contract reference for the firmware team: the HiveMQ Cloud credential flow (per-device username/password over TLS port 8883, a separate Bridge credential, Let's Encrypt cert + TLS-SNI support) and canonical payload examples the firmware can copy verbatim.

Contract (from the spec): topics `rempah/{device_id}/telemetry|state|command`; telemetry at 5s cadence `{ts, boiler_temp_c, gas_pressure_kpa, water_level, drip_count, flame_lit}`; retained state `{device_id, mode, cause, command_id?, ts}` with causes `command_executed`/`command_failed`/`detected`; command `{command_id, action}`.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Provisioning checklist document exists.
- [x] Canonical payload examples match the spec exactly.

## Comments

- 2026-08-12: Document created at `docs/mqtt-provisioning.md` — HiveMQ credential flow (per-device + Bridge credential, TLS 8883, Let's Encrypt + TLS-SNI), canonical telemetry/state/command payloads verbatim from spec, topic summary, action list.