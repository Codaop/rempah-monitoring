# 56 — Hapus sementara metric card "Perkiraan Hasil" di dashboard

**What to build:** Metric card "PERKIRAAN HASIL" pada dashboard dihapus untuk
sementara karena nilai estimasi hasil belum punya variabel perhitungan yang
jelas dan akurat. Card akan diganti dengan metric lain di kemudian hari; saat
ini tidak menampilkan angka yang menyesatkan operator.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Metric card "PERKIRAAN HASIL" tidak lagi tampil di dashboard
- [ ] Layout grid card yang tersisa tetap rapi (tidak ada lubang/kolom kosong)
- [ ] Tidak ada error runtime akibat referensi nilai yang dihapus (mis. sparkline/derived value yang masih memakai data tersebut)
