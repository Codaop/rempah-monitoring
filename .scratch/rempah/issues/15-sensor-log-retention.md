# 15 — Sensor log retention purge

**What to build:** Raw `sensor_logs` are purged once they pass the active batch plus a 7-day grace tail; only `batch_logs` aggregates survive long-term. A scheduled job (pg_cron or Bridge-side) deletes expired telemetry without ever touching an active batch.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Purge job removes `sensor_logs` past active-batch + 7 days.
- [ ] Telemetry of the active batch is never purged.
- [ ] `batch_logs` aggregates are unaffected.