-- Migration 09: kolom cooling_temp_c pada sensor_logs (sensor suhu kedua)
--
-- Latar belakang: perangkat distilasi punya dua termokopel MAX6675 — sensor 1
-- (boiler, sudah ada sebagai boiler_temp_c) dan sensor 2 (pendingin/cooling).
-- Sebelumnya suhu pendingin hanya dibaca di firmware (serial monitor) dan tidak
-- dikirim via MQTT. Kini firmware mengirim `cooling_temp_c` di telemetry agar
-- dashboard bisa menampilkan kartu "Suhu Pendingin".
-- Kolom water_level lama dibiarkan (historis + kompatibilitas).

alter table public.sensor_logs
  add column if not exists cooling_temp_c numeric;
