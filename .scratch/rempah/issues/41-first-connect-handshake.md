# 41 — Handshake koneksi pertama + notifikasi

**What to build:** Saat device pertama kali publish telemetry/state, bridge mencatat `first_seen_at` pada baris device dan membuat alert "perangkat terhubung pertama kali" yang muncul di NotificationLog dashboard — operator mendapat kepastian bahwa provisioning berhasil end-to-end (registrasi → konfigurasi → device online).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [x] Kolom `first_seen_at` (timestamptz, nullable) ada di `devices` (migrasi) dan diisi hanya sekali pada koneksi pertama
- [x] Bridge menulis `first_seen_at` saat telemetry/state pertama dari sebuah device dan tidak menimpanya saat reconnect
- [x] Alert "perangkat <nama> terhubung pertama kali" muncul di NotificationLog dashboard

## Comments

- 2026-08-14: Migrasi `devices_first_seen_at` diterapkan (scripts/migrations/06). `note_first_contact` di SupabaseDbAdapter: dedupe lewat cek `first_seen_at` yang sudah terisi, lalu UPDATE devices + INSERT alerts kind `device_first_seen`. Dipanggil dari `Bridge.handle_telemetry` & `handle_state`.
- 2026-08-14: Tes unit ditambahkan (telemetry & state merekam first contact; device tak dikenal tidak memicunya). Alert di dashboard via subscription postgres_changes UPDATE devices (first_seen_at null → terisi), tag PROVISION.
