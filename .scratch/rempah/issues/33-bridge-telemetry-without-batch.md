# 33 — Bridge: simpan telemetry walau tanpa batch aktif

**What to build:** `insert_telemetry` di bridge saat ini membuang data ketika tidak ada batch aktif (`if batch is None: return`). Ubah agar telemetry selalu disimpan ke `sensor_logs` — dengan `batch_id` NULL saat idle — sehingga dashboard bisa menampilkan nilai hidup perangkat di luar batch (mis. cek kesiapan sebelum mulai, monitoring pasif di sela-sela batch). Perhitungan yield/ETA tetap hanya berjalan saat batch aktif. Sertakan unit test.

**Blocked by:** 27 — Migration `sensor_logs.batch_id` nullable

**Status:** ready-for-agent

- [ ] Telemetry tersimpan ke `sensor_logs` meski tidak ada batch aktif (batch_id NULL)
- [ ] Yield/ETA tetap dihitung hanya saat batch aktif (tidak berubah)
- [ ] Unit test baru lolos dan suite lama tetap hijau
