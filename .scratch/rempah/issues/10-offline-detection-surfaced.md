# 10 — Offline detection surfaced

**What to build:** When a device falls silent, the operator must not fire commands into the void. The Bridge derives `devices.last_seen_at` from the telemetry/state cadence and flags the device offline after 1 minute of silence (~12 missed 5s ticks); the dashboard shows an offline indicator and warns against sending commands.

**Blocked by:** 07

**Status:** done

- [x] `devices.last_seen_at` refreshes on each telemetry/state message.
- [x] Device flagged offline after 60 seconds of silence.
- [x] Dashboard shows the offline state (red indicator) without manual refresh.

## Comments

- 2026-08-12: Implemented. Every telemetry/state message updates `devices.last_seen_at`; `Bridge.check_offline()` runs on a 30s sweep in `__main__.py` (OFFLINE_AFTER_S=60). Dashboard derives offline from `last_seen_at` (<45s) in PowerPanel — no extra column needed.