-- Migration 08: kolom gas_mass_kg pada sensor_logs (sensor beban)
-- Applied 2026-08-14 via execute_sql (MCP apply_migration bermasalah di environment ini).
--
-- Latar belakang: perangkat distilasi mengukur gas LPG dengan sensor beban
-- (load cell) — bukan pressure gauge. Kontrak telemetry berubah dari
-- `gas_pressure_kpa` menjadi `gas_mass_kg` (massa/berat tabung dalam kg).
-- Kolom `gas_pressure_kpa` lama dibiarkan (historis + kompatibilitas).

alter table public.sensor_logs
  add column if not exists gas_mass_kg numeric;
