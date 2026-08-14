# 45 — Nilai live kartu metrik dashboard ditampilkan 2 desimal

**What to build:** Operator melihat nilai Suhu Boiler, Massa Gas, dan Level Air pada kartu metrik dashboard selalu bergerak dengan **2 angka desimal** (mis. `93,44 °C`, `28,53 kg`, `65,76 %`) yang diperbarui realtime setiap telemetry masuk. Dengan presisi 2 desimal, angka terlihat berubah tiap tick (5 detik) sehingga operator yakin alat masih berjalan semestinya dan tidak berhenti — berbeda dengan tampilan 1 desimal saat ini yang sering "diam" di angka yang sama.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] Kartu metrik Suhu Boiler, Massa Gas, dan Level Air menampilkan nilai dengan 2 desimal (bukan 1 desimal seperti sekarang)
- [x] Nilai berubah pada setiap telemetry masuk (realtime) sehingga pergerakan terlihat jelas per tick
- [x] Sparkline tetap memakai data mentah 2 desimal tanpa pembulatan tambahan
- [x] Format angka konsisten dengan locale `id-ID` (pemisah desimal koma, mis. `93,44`)
- [x] Pesan alert (suhu tinggi, level air rendah) ikut menampilkan 2 desimal agar konsisten

## Comments

- 2026-08-14: Selesai di commit `6828c34`. Default `fmtNum` diubah ke 2 desimal dengan `minimumFractionDigits` tetap (mis. `28,50` bukan `28,5`), mencakup semua pemanggil (kartu metrik, sparkline tetap data mentah, alert). Build `vite build` hijau, pytest 30 passed.
