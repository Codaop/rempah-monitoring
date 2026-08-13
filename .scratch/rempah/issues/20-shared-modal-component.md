# 20 — Komponen modal dialog reusable

**What to build:** Sebuah komponen modal terpusat yang dipakai ulang oleh semua flow konfirmasi dan form berikutnya, sehingga seluruh dashboard punya pengalaman modal yang konsisten: overlay gelap, panel kartu, judul, area konten, dan area aksi. Modal tertutup dengan benar melalui tombol tutup, tombol ESC, atau klik di luar overlay, dan konten di belakangnya tidak bisa diinteraksi selama modal terbuka.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Komponen modal (overlay + panel + slot konten + slot aksi) dibuat di direktori komponen bersama dan bisa diimpor oleh komponen mana pun
- [x] Modal dapat dibuka/ditutup dengan benar: tombol tutup, tombol ESC, dan klik di luar overlay; konten di bawah tidak bisa diinteraksi saat modal terbuka
- [x] Gaya dan posisi modal konsisten (terpusat, z-index di atas semua elemen, padding aman di layar kecil, tidak melebihi tinggi viewport)
- [x] Build dashboard lulus; konsumen pertama yang benar-benar memakai komponen ini adalah ticket 22 dan 24

## Comments

- 2026-08-13: Komponen dibuat di dashboard/src/components/AppModal.vue (Teleport ke body, tutup via ESC/overlay/tombol X, kunci scroll body saat terbuka, slot konten + aksi, max-height viewport). Build lulus. Belum ada konsumen nyata sampai ticket 22/24. Diverifikasi via `npm run build`.
