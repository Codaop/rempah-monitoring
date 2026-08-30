# 64 — Revisi rendemen laporan menjadi persen (%)

**What to build:** Batch yang selesai mencatat rendemen dalam **persen (%)**
sesuai rumus `Rendemen (%) = Berat minyak atsiri ÷ Berat bahan baku × 100%`.
Berat minyak atsiri diambil dari nilai ml yang diisi operator saat batch
selesai (per kesepakatan, **1 ml = 1 gram**), dan berat bahan baku dari massa
charge batch (kg, dikonversi ke gram). Hasil persen tersimpan di database dan
tampil konsisten di halaman analitik & log, pratinjau laporan, dan PDF —
menggantikan satuan lama `ml/kg`.

**Blocked by:** None — can start immediately (revisi dari ticket 55 yang sudah
selesai; tidak bergantung ticket lain)

**Status:** ready-for-agent

- [ ] Kolom `yield_rendemen_ml_per_kg` di tabel `batch_logs` di-rename menjadi `yield_rendemen_pct` (migration + data)
- [ ] Data lama di-backfill: `yield_rendemen_pct = yield_rendemen_ml_per_kg ÷ 10` (karena persen = ml/kg ÷ 10 dengan asumsi 1 ml = 1 g)
- [ ] Perhitungan saat batch selesai memakai rumus baru: `rendemen_pct = (volume_ml ÷ (charge_kg × 1000)) × 100`
- [ ] Modal pencatatan hasil tetap meminta input volume minyak (ml) — label tidak berubah
- [ ] Halaman analitik & log menampilkan rendemen sebagai persen (mis. `3.00 %`), bukan `ml/kg`
- [ ] Pratinjau laporan dan PDF menampilkan rendemen sebagai persen
- [ ] Hint kalkulasi di modal diperbarui sesuai rumus baru (tidak lagi "volume ÷ berat → ml/kg")
- [ ] Kasus berat bahan baku 0 / kosong tetap ditangani (validasi, tidak crash)
