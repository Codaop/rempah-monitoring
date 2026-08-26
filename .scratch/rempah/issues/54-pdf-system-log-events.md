# 54 — Ganti "Kejadian Penting" dengan log sistem batch di PDF

**What to build:** Bagian "Kejadian Penting" pada laporan batch PDF diganti
dengan log sistem yang benar-benar terjadi pada batch tersebut — event dari
sumber log sistem (sensor/perintah/batch) yang muncul **setelah batch dimulai**
dan memiliki timestamp yang cocok dengan jendela batch (`>= started_at`, dan
`<= ended_at` untuk batch selesai). Daftar commands+alerts mentah saat ini tidak
mencerminkan log sistem yang dilihat operator di halaman.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] PDF menampilkan log sistem batch (bukan tabel commands+alerts mentah)
- [ ] Hanya log dengan timestamp `>= started_at` (dan `<= ended_at` bila selesai) yang masuk
- [ ] Format baris log konsisten dengan tabel "Log Sistem" di halaman Analytics
