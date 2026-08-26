-- Migration 11: volume hasil minyak & rendemen pada batch_logs (ticket 55)
--
-- Saat batch selesai, operator wajib mengisi volume minyak atsiri hasil
-- distilasi (ml, diukur gelas ukur). Bridge/tabel menyimpan:
--   oil_volume_ml          — volume hasil minyak (ml)
--   yield_rendemen_ml_per_kg — rendemen = volume (ml) / berat bahan baku (kg)
--   yield_recorded_at      — waktu operator menyerahkan nilai (untuk tanggal
--                            pencatatan laporan, bukan preview/download)

alter table public.batch_logs
  add column if not exists oil_volume_ml numeric,
  add column if not exists yield_rendemen_ml_per_kg numeric,
  add column if not exists yield_recorded_at timestamptz;
