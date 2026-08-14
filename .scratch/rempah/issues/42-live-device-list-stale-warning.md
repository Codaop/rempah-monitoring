# 42 — Live update daftar device + peringatan provisioning menggantung

**What to build:** Daftar device di Manajemen Perangkat ter-update otomatis (realtime) sehingga status Online/Offline berubah tanpa refresh manual — momen "device baru nyambung" langsung terlihat. Ditambah banner peringatan untuk device yang sudah lama terdaftar tapi belum pernah terhubung (mis. > 7 hari, `first_seen_at` masih null), dengan tautan ke panduan provisioning agar operator tidak dibiarkan menunggu device yang ternyata belum dikonfigurasi.

**Blocked by:** 40 — Lifecycle status perangkat di daftar, 41 — Handshake koneksi pertama + notifikasi

**Status:** ready-for-agent

- [x] Status device berubah live saat telemetry masuk, tanpa refresh manual
- [x] Banner peringatan muncul untuk device yang belum pernah terhubung > 7 hari sejak didaftarkan, lengkap dengan tautan panduan
- [x] Subscription realtime dibersihkan saat komponen unmount (tidak ada leak)

## Comments

- 2026-08-14: Implementasi di DeviceManager.vue — subscription postgres_changes UPDATE + INSERT `devices` (channel `device-manager-live`) memperbarui `last_seen_at`/`first_seen_at` pada baris lokal; di-cleanup di onBeforeUnmount via removeChannel. Banner `staleDevices` (created_at > 7 hari & first_seen_at null) dengan tombol "Kartu Flash" per device + tautan panduan `docs/mqtt-provisioning.md` (GitHub, target _blank). Load select device menyertakan `first_seen_at`.
