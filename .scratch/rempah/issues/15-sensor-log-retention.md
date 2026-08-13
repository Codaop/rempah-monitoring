# 15 — Sensor log retention purge

**What to build:** Raw `sensor_logs` are purged once they pass the active batch plus a 7-day grace tail; only `batch_logs` aggregates survive long-term. A scheduled job (pg_cron or Bridge-side) deletes expired telemetry without ever touching an active batch.

**Blocked by:** 07

**Status:** done

- [x] Purge job removes `sensor_logs` past active-batch + 7 days.
- [x] Telemetry of the active batch is never purged.
- [x] `batch_logs` aggregates are unaffected.

## Comments

- 2026-08-12: Implemented. `purge_old_sensor_logs()` deletes `sensor_logs` whose `batch_id` is in closed batches ended >7 days ago (active batches have `ended_at = null` and are never touched); runs daily from `__main__.py` (PURGE_INTERVAL_S). `batch_logs` untouched. Index `sensor_logs(batch_id)` added in migration 02.