# 44 — Dokumen provisioning alur web-driven (kredensial bersama)

**What to build:** `docs/mqtt-provisioning.md` diperbarui ke model kredensial bersama: satu credential HiveMQ untuk semua device (dibuat sekali di web HiveMQ console), topik root ditetapkan **`rempah/`**, pembeda antar unit = `device_id` di segmen topik + `client_id` unik per koneksi (di-set di firmware ESP32, bukan di web HiveMQ). Alur yang didokumentasikan: daftarkan via web → kartu flash berisi nilai yang perlu dikonfigurasi (UUID, topik `rempah/{device_id}/telemetry|state|command`, kredensial bersama, contoh client_id) → developer melakukan konfigurasi awal firmware di meja kerja (flash via USB/serial) → device connect WiFi + MQTT → verifikasi status "Online" di dashboard. Kartu flash adalah *lembar referensi* untuk konfigurasi awal, bukan mekanisme self-provisioning — ESP32 baru tidak punya firmware, jadi setup pertama selalu dilakukan developer secara manual. Mode WiFi-AP provisioning (kalau kelak dipakai) hanya untuk konfigurasi ulang tanpa re-flash; cukup dicatat sebagai opsi masa depan, bukan target flow saat ini.

**Blocked by:** 39 — Registrasi device dengan kredensial bersama, 41 — Handshake koneksi pertama + notifikasi

**Status:** ready-for-agent

- [ ] Dokumen menjelaskan model kredensial bersama (satu credential di HiveMQ console, topik root `rempah/`, pembeda = `device_id` di topik + `client_id` unik di firmware)
- [ ] Alur tercantum langkah per langkah: registrasi → kartu flash sebagai referensi nilai → konfigurasi awal firmware oleh developer (USB/serial) → verifikasi online di dashboard
- [ ] Dokumen menjelaskan bahwa `client_id` unik (mis. `client-<device_id>`) di-set di firmware ESP32, bukan di web HiveMQ console — dan bahwa setup pertama selalu manual oleh developer (ESP32 baru tidak punya firmware); WiFi-AP provisioning hanya dicatat sebagai opsi konfigurasi ulang masa depan
