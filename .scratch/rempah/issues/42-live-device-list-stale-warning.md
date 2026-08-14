# 42 — Live update daftar device + peringatan provisioning menggantung

**What to build:** Daftar device di Manajemen Perangkat ter-update otomatis (realtime) sehingga status Online/Offline berubah tanpa refresh manual — momen "device baru nyambung" langsung terlihat. Ditambah banner peringatan untuk device yang sudah lama terdaftar tapi belum pernah terhubung (mis. > 7 hari, `first_seen_at` masih null), dengan tautan ke panduan provisioning agar operator tidak dibiarkan menunggu device yang ternyata belum dikonfigurasi.

**Blocked by:** 40 — Lifecycle status perangkat di daftar, 41 — Handshake koneksi pertama + notifikasi

**Status:** ready-for-agent

- [ ] Status device berubah live saat telemetry masuk, tanpa refresh manual
- [ ] Banner peringatan muncul untuk device yang belum pernah terhubung > 7 hari sejak didaftarkan, lengkap dengan tautan panduan
- [ ] Subscription realtime dibersihkan saat komponen unmount (tidak ada leak)
