# 51 — Waktu selesai riil & durasi batch di laporan PDF

**What to build:** Laporan batch PDF menampilkan waktu selesai yang sesuai
keadaan nyata di lapangan dan durasi yang dihitung dari selisih waktu selesai
dikurangi waktu mulai. Saat ini durasi tidak pernah muncul karena nilai durasi
disimpan sebagai interval ISO (`PT{n}S`) namun di-parse sebagai angka, sehingga
hasilnya tidak valid.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] "Selesai" di PDF menampilkan waktu riil batch berakhir (bukan timestamp device yang salah; pastikan batch benar-benar ter-close)
- [ ] "Durasi" di PDF terisi dari selisih `ended_at − started_at` (parse interval ISO `PT{n}S` atau hitung langsung dari kedua timestamp)
- [ ] Batch yang belum selesai (status bukan completed) menampilkan placeholder yang jujur, bukan angka menyesatkan
