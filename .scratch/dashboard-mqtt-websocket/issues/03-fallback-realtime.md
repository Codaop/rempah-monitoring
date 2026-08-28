# 03 — Fallback otomatis ke jalur Supabase Realtime saat WS terputus

**What to build:** Saat koneksi MQTT WebSocket terputus atau sedang
reconnecting, nilai live otomatis kembali ke jalur yang sudah ada (Supabase
Realtime + polling). Saat koneksi pulih, kembali ke MQTT tanpa reload.
Indikator di UI menunjukkan jalur mana yang sedang aktif.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Matikan broker/jaringan → card tetap menampilkan data dari Supabase;
      tidak ada error fatal di konsol.
- [ ] Pulihkan koneksi → kembali ke aliran MQTT secara otomatis tanpa reload.
- [ ] Tidak ada duplikasi nilai atau lompatan angka yang salah saat perpindahan
      jalur.
