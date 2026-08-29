# 57 — Fondasi data: status `interrupted` + `interrupted_at`

**What to build:** Database mampu menyimpan bahwa sebuah batch terputus di tengah
jalan (mesin mati mendadak / disconnect) tanpa menyebutnya selesai. Batch yang
terputus bisa ditandai `interrupted` dengan waktu pemutusan yang tercatat, dan
masih bisa dikembalikan ke `active` (resume) nanti.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Kolom `batches.interrupted_at timestamptz` (nullable) tersedia via migrasi
- [ ] Batch dapat di-set `status = 'interrupted'` + `interrupted_at` — tidak ada
      constraint/RLS yang menolak nilai status baru (status `text` bebas)
- [ ] Batch `interrupted` dapat dikembalikan ke `active` (resume) tanpa mengubah
      `started_at`; `interrupted_at` dibersihkan saat resume
- [ ] Data batch lama (`completed`/`active`) tidak berubah oleh migrasi ini
