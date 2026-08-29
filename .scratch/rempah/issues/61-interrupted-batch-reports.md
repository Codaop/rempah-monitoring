# 61 — Batch `interrupted` di laporan & analitik (Opsi A)

**What to build:** Batch yang terputus (status `interrupted`) ditampilkan secara
transparan di laporan dan analitik — konsisten dengan prinsip "status jujur"
(ticket 31, 51). Laporan PDF menampilkan batch `interrupted` dengan label
**"Terputus"** dan kolom waktu selesai/durasi yang jujur (tidak mengarang angka:
durasi dari `started_at` sampai `interrupted_at`, bukan seolah selesai normal).
Halaman analitik tetap menampilkan batch `interrupted` di daftar riwayat, tapi
mengecualikannya dari agregat keberhasilan/rendemen penuh agar tidak dianggap
sebagai batch yang selesai.

**Blocked by:** 58 — Deteksi pemutusan di bridge: batch otomatis `interrupted`

**Status:** ready-for-agent

- [ ] Laporan PDF menampilkan batch `interrupted` dengan label "Terputus";
      kolom waktu selesai/durasi jujur (tidak mengarang angka)
- [ ] Batch `interrupted` tidak muncul sebagai "Selesai" di mana pun di laporan
- [ ] Analitik menampilkan batch `interrupted` di daftar riwayat tapi
      mengecualikannya dari perhitungan hasil/rendemen/keberhasilan penuh
- [ ] Tidak ada angka menyesatkan (mis. yield seolah tercapai penuh) untuk batch
      yang terputus
