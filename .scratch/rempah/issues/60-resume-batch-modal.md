# 60 — Modal konfirmasi resume batch di dashboard

**What to build:** Saat perangkat kembali online dan ternyata punya batch
`interrupted`, dashboard menampilkan modal konfirmasi dengan dua pilihan:
**"Lanjutkan Batch"** (mengirim `RESUME_BATCH` + `POWER_ON` — batch balik
`active` dan lanjut dari titik terputus) atau **"Mulai Batch Baru"** (batch lama
tetap tertutup sebagai `interrupted`, form batch baru terbuka). Operator
memutuskan nasib batch terputus lewat satu dialog yang jelas, bukan dibiarkan
menggantung.

**Blocked by:** 59 — Command resume batch dari dashboard (RESUME_BATCH)

**Status:** ready-for-agent

- [ ] Modal muncul otomatis saat device online kembali & ada batch `interrupted`
      untuk device itu; tidak muncul saat tidak ada batch terputus
- [ ] "Lanjutkan Batch" → mengirim `RESUME_BATCH` + `POWER_ON`; panel batch
      menampilkan batch yang sama kembali `active`
- [ ] "Mulai Batch Baru" → batch lama tetap `interrupted` (masuk riwayat), form
      batch baru terbuka seperti alur normal
- [ ] Modal tidak muncul berulang/menumpuk saat auto-refresh (state sudah
      diselesaikan); UI konsisten dengan desain sistem (AppModal + token)
