# 55 — Alur kalkulasi rendemen minyak atsiri saat batch selesai

**What to build:** Alur kerja (workflow) rendemen minyak atsiri yang berjalan
otomatis ketika sebuah batch mencapai status **Completed/Selesai**:

1. **Trigger:** Saat proses "Batch 1" mencapai status `completed`.
2. **UI Component:** Muncul modal/pop-up dialog dengan **satu input wajib**
   (required) — **Volume Hasil Minyak Atsiri** dalam **ml** (hasil akhir,
   per-batch, diukur dengan gelas ukur) — tidak bisa dilewati/ditutup tanpa
   mengisi.
3. **State Management:** Sistem mengambil **Berat Bahan Baku** (massa kapulaga,
   kg) yang sudah diinput dan disimpan di awal sesi batch (dari data batch yang
   sudah ada).
4. **Logic & Computation:** Hitung rendemen secara asinkron di background
   segera setelah Volume Minyak di-submit:
   `Rendemen (ml/kg) = (Volume Minyak Hasil [ml] / Berat Bahan Baku [kg])` —
   satuan ml/kg (praktik industri atsiri); lihat catatan konversi % di bawah.
5. **Expected Output:** Komponen UI pada halaman **Laporan (Report)** otomatis
   me-render hasil rendemen, dan hasilnya **disimpan ke database**.

**Blocked by:** None — can start immediately (rumus dan alur sudah ditetapkan)

**Status:** ready-for-agent

- [ ] Modal wajib (required) "Volume Hasil Minyak (ml)" muncul saat batch berstatus completed
- [ ] Modal hanya berisi satu input wajib (volume ml) — bukan massa; ticket 57 (volume terpisah) digabung ke sini
- [ ] Sistem mengambil Berat Bahan Baku (kg) dari data batch yang tersimpan di awal sesi
- [ ] Rendemen dihitung asinkron sebagai ml/kg: `(Volume Minyak [ml] / Berat Bahan Baku [kg])`
- [ ] Hasil rendemen tersimpan ke database (kolom volume minyak + kolom rendemen pada data batch)
- [ ] Halaman Laporan (Report) me-render nilai rendemen secara otomatis
- [ ] Kasus Berat Bahan Baku = 0 / kosong ditangani (tidak crash, validasi input)

**Catatan satuan:** Volume minyak diukur dalam ml (gelas ukur), bahan baku dalam
kg — jadi hasil rendemen adalah **ml/kg** (metrik umum industri atsiri), bukan
persen murni. Jika kelak ingin ditampilkan sebagai % murni, perlu konversi via
densitas minyak (opsi B, di luar cakupan saat ini).

### Task tambahan — Tanggal "Dibuat" pada laporan sesuai waktu pencatatan (bukan preview/download)

**What to build:** Di halaman Laporan, label "Dibuat" saat ini memakai waktu
*saat pengguna preview/download* PDF. Seharusnya tanggal "Dibuat" adalah
waktu laporan tercatat di database — yaitu saat batch selesai dan agregat
laporan akhir ditulis ke `batch_logs` (`created_at` batch_logs, atau fallback
`batches.ended_at` bila batch_logs belum ada).

- [ ] Label "Dibuat" pada laporan memakai `batch_logs.created_at` (atau fallback `batches.ended_at`), bukan `new Date()` saat preview/download
- [ ] Tanggal dibuat konsisten di PDF dan preview laporan
