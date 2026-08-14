# 46 — Presisi 2 desimal konsisten di tabel log & laporan Analitik

**What to build:** Nilai sensor pada halaman "Analitik & Log" ditampilkan konsisten dengan dashboard: tabel kejadian (Lonjakan Suhu Boiler, Massa Gas), ringkasan batch, preview, dan laporan PDF/print memakai 2 desimal (mis. `93,44 °C`, `28,53 kg`, `65,76 %`). Konsistensi ini penting agar operator yang berpindah antara dashboard dan analitik tidak melihat angka yang beda presisi untuk data yang sama.

**Blocked by:** None — can start immediately (paralel dengan 45; keduanya hanya mengubah tampilan, bukan data).

**Status:** resolved

- [x] Tabel kejadian menampilkan nilai sensor dengan 2 desimal
- [x] Ringkasan batch & preview laporan menampilkan 2 desimal
- [x] Laporan PDF/print menampilkan 2 desimal yang konsisten
- [x] Massa muatan di panel batch menampilkan 2 desimal
- [x] Tidak ada perubahan kontrak telemetry / data mentah — murni perubahan tampilan

## Comments

- 2026-08-14: Selesai di commit `6828c34` bersama ticket 45 — semua pemanggil `fmtNum` memakai default baru 2 desimal (`id-ID`, koma), termasuk tabel kejadian, ringkasan batch, preview, dan PDF/print. Data mentah tidak diubah.
