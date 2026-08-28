# 04 — Dokumentasi konfigurasi, keterbatasan, & panduan verifikasi manual

**What to build:** Dokumentasi environment variable baru untuk koneksi MQTT
WebSocket dashboard, catatan kredensial (memakai user yang sama dengan device —
ekspos di bundle browser), verifikasi port WSS di HiveMQ console, keterbatasan
free tier tanpa ACL (mitigasi filtering client-side), serta skenario verifikasi
manual untuk seluruh alur.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Dokumentasi menyebutkan `VITE_MQTT_URL` / `VITE_MQTT_USERNAME` /
      `VITE_MQTT_PASSWORD` beserta cara mengisinya.
- [ ] Skenario verifikasi manual tercantum: bridge mati, jaringan/broker putus,
      perintah tetap jalan, laporan PDF utuh, pengukuran delay.
- [ ] Catatan keterbatasan terdokumentasi: tanpa ACL di free tier → filtering
      client-side; kredensial publik di bundle → rotasi menyentuh firmware +
      dashboard.
