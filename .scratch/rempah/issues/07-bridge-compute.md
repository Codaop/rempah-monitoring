# 07 — Bridge compute: estimated yield, estimated finish, over-temperature alerts

Status: ready-for-agent

## Problem

The dashboard needs progress estimates and hybrid alerts that the device does not and should not compute.

## Requirements

- **Estimated Yield** (liters) computed by the Bridge from telemetry and drip data against the batch's target (`batches.target_yield_l`, derived from Charge Mass).
- **Estimated finish time** computed from progress and rate of drip accumulation.
- **Over-temperature alert** raised when `boiler_temp_c` exceeds a configured threshold (env-config tunable); device-detected binary alerts (flame-out, low water, end-point) pass through from state messages without Bridge computation.
- Results land in `batch_logs` (`estimated_yield`, `estimated_finish_at`) and feed the dashboard's "Perkiraan Hasil" card.

## Acceptance

- Bridge-computed estimates update as drip/telemetry arrive.
- Over-temperature alert fires at/above threshold and clears below it.
- Given the spec's founding suite, tests assert computed values against independent worked examples (not recomputation).

Blocked by: 01, 02