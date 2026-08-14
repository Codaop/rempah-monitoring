-- Migration 06: kolom first_seen_at pada devices (ticket 41)
-- Applied 2026-08-13 as migration `devices_first_seen_at`.
--
-- Latar belakang: handshake provisioning — ketika device pertama kali publish
-- telemetry/state, bridge mencatat first_seen_at (diisi sekali, tidak ditimpa
-- saat reconnect) sebagai penanda bahwa device sudah berhasil dikonfigurasi
-- dan terhubung. Dipakai juga oleh ticket 42 (peringatan provisioning
-- menggantung: device terdaftar tapi tidak pernah first_seen).

alter table public.devices
  add column if not exists first_seen_at timestamptz;
