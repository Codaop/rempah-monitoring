-- Migration 07: unknown_messages table (ticket 43)
-- Applied 2026-08-14 as migration `unknown_messages_table` (via execute_sql;
-- apply_migration MCP tool was erroring, DDL applied directly).
--
-- Pesan MQTT (telemetry/state) dari device_id yang tidak terdaftar di `devices`
-- tidak bisa masuk tabel `alerts` (FK device_id NOT NULL ke devices), jadi
-- kejadian dicatat di tabel ini tanpa FK agar bridge tidak crash dan operator
-- bisa mendiagnosis device liar / salah konfigurasi dari dashboard.

create table if not exists public.unknown_messages (
  id uuid primary key default gen_random_uuid(),
  device_id text not null,
  topic text not null,
  payload jsonb,
  ts timestamptz not null default now()
);

alter table public.unknown_messages enable row level security;

-- Operator (authenticated) dapat membaca pesan device tak dikenal untuk
-- didiagnosis; penulisan hanya dari bridge via service_role (bypass RLS).
create policy "operators read unknown messages"
  on public.unknown_messages for select
  to authenticated
  using (true);
