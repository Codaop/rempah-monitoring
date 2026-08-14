# 39 — Registrasi device dengan kredensial bersama (shared credential)

**What to build:** Operator mendaftarkan device baru cukup dengan nama — sistem TIDAK lagi meng-generate kredensial per-device (`device-<id>` + password acak seperti ticket 36). Kartu flash provisioning menampilkan UUID device, tiga topik MQTT, dan kredensial MQTT **bersama** (satu username/password yang sama untuk semua device) yang diambil dari konfigurasi env dashboard; jika belum dikonfigurasi, tampilkan instruksi menghubungi admin. Rotasi per-device tidak lagi relevan — rotasi kredensial bersama dilakukan di level broker/admin dan didokumentasikan (lihat ticket 44).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [x] Registrasi membuat baris `devices` milik producer operator tanpa meng-generate `mqtt_username`/`mqtt_password` per-device
- [x] Kartu flash menampilkan UUID, topik `rempah/{device_id}/telemetry|state|command` (root sudah ditetapkan `rempah`), dan kredensial bersama (dari env; fallback pesan "hubungi admin" bila tidak terisi)
- [x] Kartu flash memuat catatan panduan client_id unik per unit (mis. `client-<device_id>`) — ditulis di firmware, bukan konfigurasi web HiveMQ
- [x] Bagian kredensial per-device dihapus dari kartu flash; tidak ada referensi sisa
- [x] Alur kredensial per-device (ticket 36) tidak lagi dipakai — kolom `devices.mqtt_username`/`mqtt_password` tidak diisi pada registrasi baru

## Comments

- 2026-08-13: Berasal dari keputusan tim — budget terbatas, HiveMQ free tier; satu credential untuk semua device, pembeda lewat `device_id` di topik dan `client_id` unik per ESP32. Menggantikan rancangan awal "rotasi kredensial per-device" yang tidak relevan di model ini.
- 2026-08-13: Kartu flash adalah **lembar referensi** untuk konfigurasi awal firmware oleh developer (flash via USB/serial), bukan mekanisme self-provisioning — ESP32 baru tidak punya firmware, jadi setup pertama selalu manual. Karena kredensial kini bersama (bukan rahasia per-device), penguncian "hanya ditampilkan sekali" pada kartu flash bisa dihapus/dilonggarkan; UUID + topik tetap bisa dilihat kembali dari daftar (ticket 38).
- 2026-08-13: Keputusan tim — topik root ditetapkan **`rempah/`** (bukan env configurable lagi); `client_id` unik per unit (mis. `client-<device_id>`) adalah pengaturan di **firmware ESP32**, bukan di web HiveMQ console — web HiveMQ hanya untuk membuat credential bersama sekali.
- 2026-08-14: Implementasi selesai di DeviceManager.vue — TOPIC_ROOT hardcoded `rempah`, registrasi hanya INSERT `{producer_id, name}` (tanpa generate kredensial per-device), kredensial bersama dari env (`VITE_MQTT_DEVICE_USERNAME`/`VITE_MQTT_DEVICE_PASSWORD`, didokumentasikan di dashboard/.env.example) dengan fallback "hubungi admin", kartu flash (baru & reflash) menampilkan UUID, topik rempah, kredensial bersama, dan catatan client_id di firmware. Kolom tabel "MQTT USERNAME" diganti "DIDAFTARKAN". Build dashboard hijau.
