# 11 — Bridge compute: estimated yield/ETA + over-temperature alerts

**What to build:** Against the batch's target (`batches.target_yield_l`, derived from Charge Mass), the Bridge computes estimated yield from drip accumulation and estimated finish time from progress and drip rate; it raises an over-temperature alert when `boiler_temp_c` exceeds an env-tunable threshold. Device-detected binary alerts (flame-out, low water, end-point) pass through without Bridge computation. Results land in `batch_logs` (`estimated_yield`, `estimated_finish_at`) and feed the dashboard's "Perkiraan Hasil" card and notification log.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] `estimated_yield` / `estimated_finish_at` update as telemetry arrives, verified against independent worked examples (not recomputation).
- [ ] Over-temperature alert fires at/above the threshold and clears below it.
- [ ] Device-detected binary alerts pass through with no Bridge computation.