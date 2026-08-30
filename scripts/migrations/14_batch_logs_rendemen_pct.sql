-- Migration 14: rendemen persen pada batch_logs (ticket 64)
--
-- Revisi rumus rendemen:
--   Rendemen (%) = Berat minyak atsiri / Berat bahan baku × 100%
-- Berat minyak atsiri diambil dari nilai ml yang diisi operator (1 ml = 1 g),
-- berat bahan baku dari charge batch (kg, dikonversi ke gram).
--
-- Kolom lama `yield_rendemen_ml_per_kg` di-rename menjadi `yield_rendemen_pct`.
-- Data lama dikonversi: persen = ml/kg ÷ 10 (karena persen = ml/kg ÷ 10
-- dengan asumsi 1 ml = 1 g dan charge dikali 1000).

alter table public.batch_logs
  rename column yield_rendemen_ml_per_kg to yield_rendemen_pct;

update public.batch_logs
  set yield_rendemen_pct = yield_rendemen_pct / 10
  where yield_rendemen_pct is not null;
