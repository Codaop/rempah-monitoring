# 49 — Panel batch: hapus progress bar & estimasi selesai dari input operator

**What to build:** Operator yang membuka panel batch tidak lagi melihat progress bar
persentase. Sebagai gantinya, saat menambah batch baru operator memasukkan
**perkiraan waktu selesai** (datetime) melalui form — nilai ini ditampilkan di
panel batch sebagai "Waktu Selesai (Estimasi)" dan dipakai sebagai acuan di
laporan. Target hasil tidak lagi diinput manual (tetap dihitung otomatis oleh
bridge dari massa muatan × rasio).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Progress bar (bar + persen) dihapus sepenuhnya dari panel batch
- [ ] Form tambah batch: field "Target Hasil (L)" diganti "Perkiraan Waktu Selesai" (datetime-local, opsional)
- [ ] Insert batch menyimpan `estimated_finish_at` (bukan `target_yield_l` dari input)
- [ ] Panel batch menampilkan "Waktu Selesai (Estimasi)" dari nilai yang diinput operator
- [ ] Tabel `batches` punya kolom `estimated_finish_at` (migration 10)
