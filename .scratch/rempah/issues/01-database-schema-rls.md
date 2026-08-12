# 01 — Supabase schema + Row-Level Security

Status: done

## Problem

The Supabase database does not yet exist. Ship the schema described in `.scratch/rempah/spec.md` (Implementation Decisions → Database) and the RLS policies that scope every dashboard read/write by the operator's `producer_id`.

## Requirements

- Tables: producers, operators, devices, sessions, session_devices, batches, sensor_logs, batch_logs, device_state, commands.
- `batches` carries `charge_mass_kg` and `target_yield_l` (Charge Mass / target, per spec); `batch_logs` carries Bridge-computed `estimated_yield`, `estimated_finish_at`.
- `producer_id` on every table.
- `commands.expected_state` nullable (Emergency Stop has no expectation).
- RLS policies: operators read/write only rows whose `producer_id` matches their own; `service_role` (Bridge) bypasses RLS.

## Acceptance

- A migration script creates the schema and policies.
- Non-owner operator queries return zero/scoped rows.
- Service-role writes (simulating the Bridge) succeed regardless of policies.

## Comments

- 2026-08-11: Applied migration `rempah_schema_and_rls` to project `qjroojbtquvrdgawxcrw` (REM-PAH). All 10 tables created, `producer_id` on every table, RLS enabled via `public.operator_producer_id()` (security definer helper), indexes added, `pgcrypto` enabled. Verified: login as seeded operator returns only that producer's rows; service-role writes bypass RLS.
- 2026-08-11: Realtime enabled on `sensor_logs`, `device_state`, `batches`, `commands` (`replica identity full`).