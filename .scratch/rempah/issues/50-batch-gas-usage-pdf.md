# 50 — Penggunaan gas (load cell) tercatat & masuk laporan PDF batch

**What to build:** Sistem massa gas menghitung konsumsi gas per batch: massa gas
(load cell) tercatat saat batch mulai distilling dan massa akhir tercatat saat
batch selesai; selisih keduanya menjadi **penggunaan gas** yang ditampilkan di
laporan batch PDF (dan preview laporan). Data bersumber dari `gas_mass_kg` di
telemetry — tidak butuh input manual operator.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Bridge merekam `gas_start_kg`, `gas_end_kg`, `gas_used_kg` saat menutup batch (dari `sensor_logs.gas_mass_kg` batch)
- [ ] Tabel `batch_logs` punya kolom gas (migration 10)
- [ ] Laporan PDF batch menampilkan baris "Penggunaan Gas" (dengan rincian awal → akhir bila tersedia)
- [ ] Preview laporan di Analytics menampilkan "Penggunaan Gas"
