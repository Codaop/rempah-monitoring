# 25 — Batasi tinggi daftar opsi pada dropdown/picker

**What to build:** Semua daftar opsi berbentuk dropdown/picker kustom (pemilih perangkat di panel daya, daftar perangkat di modal form batch, dan daftar pemilihan kustom lainnya) diberi tinggi maksimum dengan scroll di dalamnya, sehingga daftar panjang tidak memanjang melebihi layar dan tetap mudah digulir.

**Blocked by:** 22, 24

**Status:** done

- [x] Pemilih perangkat di panel daya: daftar menggulir di dalamnya sendiri saat opsi banyak
- [x] Daftar perangkat di modal form batch baru: tinggi dibatasi dengan scroll internal
- [x] Daftar pemilihan kustom lain yang ada di dashboard mengikuti aturan yang sama
- [x] Tampilan konsisten: scrollbar halus, item terakhir tidak terpotong, tidak ada scroll ganda yang janggal
- [x] Catatan cakupan: dropdown native browser (mis. filter log, pemilih batch laporan) tidak bisa dibatasi tingginya — di luar cakupan ticket ini

## Comments

- 2026-08-13: Kedua daftar kustom sudah diberi batas tinggi + scroll internal: `.device-picker` di PowerPanel (max-height 220px) dan `.pick-list` di modal BatchPanel (max-height 240px) — keduanya diterapkan saat penulisan ulang komponen di ticket 22/24. Tidak ada daftar kustom lain di dashboard. Dropdown native (`<select>` di Analytics) memang tidak bisa dibatasi popup-nya oleh browser — sesuai catatan cakupan. Diverifikasi via `npm run build`.
