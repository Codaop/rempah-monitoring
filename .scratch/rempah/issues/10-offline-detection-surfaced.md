# 10 — Offline detection surfaced

**What to build:** When a device falls silent, the operator must not fire commands into the void. The Bridge derives `devices.last_seen_at` from the telemetry/state cadence and flags the device offline after 1 minute of silence (~12 missed 5s ticks); the dashboard shows an offline indicator and warns against sending commands.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] `devices.last_seen_at` refreshes on each telemetry/state message.
- [ ] Device flagged offline after 60 seconds of silence.
- [ ] Dashboard shows the offline state (red indicator) without manual refresh.