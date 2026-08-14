# 35 — Dashboard: kartu metrik hidup saat IDLE

**What to build:** `Dashboard.vue` membaca baris `sensor_logs` terbaru apa pun status batch-nya — tidak lagi bergantung pada adanya batch aktif. Saat perangkat IDLE, kartu suhu/gas/air tetap menampilkan nilai langsung dari perangkat (dengan keterangan bahwa ini nilai real-time, belum ada batch). Operator bisa cek kesiapan (air, suhu, api) sebelum menekan "Mulai Batch Baru".

**Blocked by:** 33 — Bridge simpan telemetry tanpa batch aktif

**Status:** ready-for-agent

- [ ] Kartu metrik menampilkan nilai terbaru saat perangkat IDLE (tanpa batch aktif)
- [ ] Ada indikasi/keterangan bahwa nilai berasal langsung dari perangkat, bukan dari batch
- [ ] Realtime & polling tetap memperbarui nilai saat idle
