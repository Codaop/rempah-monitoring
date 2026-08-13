-- Migration 02: alerts table + sensor_logs retention index
-- Applied 2026-08-12 as migration `alerts_table_and_sensor_logs_index`.
--
-- Notes vs. earlier draft:
-- - No unique index on batch_logs(batch_id): batch_id is already the PRIMARY KEY,
--   which is what the Bridge's upsert (on_conflict="batch_id") needs.
-- - No INSERT policy on alerts: writes come from the Bridge via service_role,
--   which bypasses RLS; an open with-check policy would let any operator write.

-- Tabel alerts: menyimpan alert hasil komputasi Bridge (over-temperature)
-- dan alert biner device-detected (flame-out, low water, end-point).
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  producer_id uuid not null references public.producers (id),
  device_id uuid not null references public.devices (id),
  kind text not null, -- over_temperature | flame_out | low_water | endpoint
  value numeric,
  ts timestamptz not null default now()
);

alter table public.alerts enable row level security;

create policy "operators read own alerts"
  on public.alerts for select
  using (producer_id = public.operator_producer_id());

-- Index pendukung purge retention pada sensor_logs.batch_id.
create index if not exists sensor_logs_batch_id_idx on public.sensor_logs (batch_id);
