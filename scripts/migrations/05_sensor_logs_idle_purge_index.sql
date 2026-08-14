-- Migration 05: partial index untuk purge baris idle sensor_logs
-- Applied 2026-08-13 as migration `sensor_logs_idle_purge_index`.
--
-- Latar belakang: ticket 33 membuat bridge menyimpan telemetry walau tidak ada
-- batch aktif (batch_id NULL). Agar purge retention (purge_old_sensor_logs)
-- bisa membersihkan baris idle >7 hari tanpa full scan, ditambahkan partial
-- index pada (ts) khusus baris dengan batch_id NULL.

create index if not exists sensor_logs_idle_ts_idx
  on public.sensor_logs (ts)
  where batch_id is null;
