# 36 — Form registrasi device + kartu flash provisioning

**What to build:** Di section "Manajemen Perangkat" pada halaman Pengaturan: form input nama perangkat → membuat baris baru di tabel `devices` (UUID dari database, `mqtt_username` otomatis `device-xxxx`, password acak) → menampilkan kartu flash berisi UUID perangkat, topic MQTT lengkap (`{root}/{device_id}/telemetry|state|command`), dan kredensial untuk ditempel ke HiveMQ console & firmware ESP32. Operator dapat menyalin kredensial untuk mem-flash perangkat asli.

**Blocked by:** 28 — RLS daftarkan device, 34 — Halaman Pengaturan section separator

**Status:** ready-for-agent

- [ ] Form berhasil membuat baris `devices` baru milik producer operator (RLS aman)
- [ ] Kartu flash menampilkan UUID, topic lengkap, dan kredensial MQTT yang bisa disalin
- [ ] Ada konfirmasi bahwa kredensial ditampilkan sekali (keamanan) atau tombol "tampilkan lagi"
