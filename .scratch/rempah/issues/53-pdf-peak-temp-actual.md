# 53 — Suhu puncak laporan = nilai tertinggi aktual batch

**What to build:** "Suhu Puncak" pada laporan batch PDF (dan preview) menampilkan
nilai `boiler_temp_c` tertinggi yang benar-benar tercatat selama batch, bukan
angka yang lebih rendah dari kenyataan lapangan. Perhitungan diverifikasi di
bridge (saat menutup batch) dan/atau fallback di dashboard.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Nilai "Suhu Puncak" di PDF sama dengan maksimum `boiler_temp_c` pada `sensor_logs` batch
- [ ] Penyebab ketidaksesuaian didiagnosa (mis. subset row, timestamp, atau purging) dan diperbaiki
- [ ] Preview laporan menampilkan nilai puncak yang sama
