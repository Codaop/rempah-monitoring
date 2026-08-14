# 40 — Lifecycle status perangkat di daftar

**What to build:** Daftar device di Manajemen Perangkat menampilkan status yang jujur berdasarkan `last_seen_at`: `Menunggu koneksi pertama` (belum pernah ada telemetry), `Online` (terakhir terlihat < 60 detik), `Offline` (lebih dari itu). State "Belum ter-provision" tidak lagi ada karena kredensial kini bersama — setiap device terdaftar langsung siap dikonfigurasi.

**Blocked by:** 39 — Registrasi device dengan kredensial bersama

**Status:** ready-for-agent

- [x] Device tanpa `last_seen_at` tampil "Menunggu koneksi pertama"
- [x] Device dengan `last_seen_at` segar tampil "Online"; yang kedaluwarsa (> 60 s) tampil "Offline"
- [x] Tidak ada lagi state "Belum ter-provision" yang menyesatkan di daftar maupun kartu flash

## Comments

- 2026-08-13: Bergantung pada 39 karena makna state berubah — di model kredensial bersama, semua device terdaftar langsung provisionable, jadi pembeda status murni dari `last_seen_at`.
- 2026-08-14: Implementasi di DeviceManager.vue — `deviceStatus(d)` 3 state (wait/ok/off); chip status baru `.wait` (abu-abu) untuk "Menunggu koneksi pertama"; tooltip menampilkan waktu terakhir terlihat. Kartu flash tidak lagi memakai istilah "belum ter-provision".
