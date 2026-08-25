-- Migration 10: perkiraan waktu selesai (input operator) + penggunaan gas
--
-- 1. batches.estimated_finish_at — perkiraan waktu selesai yang DIINPUT operator
--    lewat form tambah batch baru (menggantikan target hasil di form; target
--    hasil tetap dihitung otomatis oleh bridge dari charge × YIELD_RATIO).
-- 2. batch_logs.gas_start_kg / gas_end_kg / gas_used_kg — rekam massa gas
--    (load cell) di awal & akhir batch; selisih = penggunaan gas untuk laporan PDF.

alter table public.batches
  add column if not exists estimated_finish_at timestamptz;

alter table public.batch_logs
  add column if not exists gas_start_kg numeric,
  add column if not exists gas_end_kg numeric,
  add column if not exists gas_used_kg numeric;
