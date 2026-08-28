# 01 — Fondasi koneksi MQTT WebSocket & live store per device

**What to build:** Browser terhubung langsung ke broker HiveMQ via MQTT over
WebSocket (WSS) memakai kredensial yang sama dengan device, subscribe ke topik
telemetry & state, mem-parse dan menyimpan nilai live per device, menyaring
hanya device milik operator, serta menampilkan indikator status koneksi di
dashboard. Tanpa konfigurasi MQTT, dashboard tetap berjalan normal lewat jalur
Supabase yang ada (tanpa error).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Dashboard connect ke broker HiveMQ (WSS) memakai kredensial device yang
      sama; status koneksi (connecting / connected / reconnecting / offline)
      terlihat di UI.
- [ ] Pesan telemetry & state ter-parse dan tersimpan per device_id; hanya
      device dalam daftar milik operator yang disimpan.
- [ ] Ring buffer 60 titik per metrik per device tersedia untuk sparkline.
- [ ] Port WSS & path terverifikasi di HiveMQ console (default
      `wss://<host>:8884/mqtt`) dan terdokumentasi.
- [ ] Bila `VITE_MQTT_*` tidak di-set, dashboard tetap berfungsi via jalur
      Supabase tanpa error di konsol selain peringatan konfigurasi.
