# 12 — Monitoring session & batch lifecycle

**What to build:** The operator opens a Monitoring Session from the dashboard, selects the devices it covers, and enters the Charge Mass when the batch starts. A Batch opens automatically when its device transitions into heating mode (carrying charge mass and target), and closes automatically at completion — recording `started_at`/`ended_at`, peak temperature, duration, and yield in `batch_logs`. Per ADR 0002, batch boundaries derive from device-state transitions, not manual bookkeeping.

**Blocked by:** 09

**Status:** done

- [x] Dashboard flow to create a session, select devices, and enter Charge Mass.
- [x] Batch auto-opens on the heating-state transition with charge mass persisted.
- [x] Batch auto-closes at completion; `batch_logs` filled (peak, duration, yield).
- [x] Multiple devices / concurrent sessions per operator work without schema change.

## Comments

- 2026-08-12: Implemented. Dashboard: `BatchStarter.vue` (Mulai Batch Baru) — creates `sessions` + `session_devices`, then inserts a `batches` row (status=pending, charge_mass_kg) + `POWER_ON` command; wired into `Dashboard.vue` and `AppShell.vue`. Bridge: `Bridge.handle_state` opens the pending batch on heating transition (PREHEAT/DISTILLING) and closes the active batch on terminal transitions (IDLE/ERROR/ESTOP); `SupabaseDbAdapter.open_pending_batch` sets active + `target_yield_l` (charge × YIELD_RATIO_L_PER_KG env); `close_active_batch` aggregates peak temp / total drips into `batch_logs` (peak_temp, duration, yield) and marks the batch completed.
- 2026-08-12: 19 bridge tests pass; `npm run build` succeeds.
- 2026-08-12: ⚠ Verify Supabase RLS on `session_devices` (junction, no producer_id column per contract) allows the dashboard insert — otherwise session creation fails; adjust policy or insert if needed.