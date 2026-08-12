# 12 — Monitoring session & batch lifecycle

**What to build:** The operator opens a Monitoring Session from the dashboard, selects the devices it covers, and enters the Charge Mass when the batch starts. A Batch opens automatically when its device transitions into heating mode (carrying charge mass and target), and closes automatically at completion — recording `started_at`/`ended_at`, peak temperature, duration, and yield in `batch_logs`. Per ADR 0002, batch boundaries derive from device-state transitions, not manual bookkeeping.

**Blocked by:** 09

**Status:** ready-for-agent

- [ ] Dashboard flow to create a session, select devices, and enter Charge Mass.
- [ ] Batch auto-opens on the heating-state transition with charge mass persisted.
- [ ] Batch auto-closes at completion; `batch_logs` filled (peak, duration, yield).
- [ ] Multiple devices / concurrent sessions per operator work without schema change.