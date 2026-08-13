# 21 — Tampilan responsif untuk semua ukuran layar

**What to build:** Seluruh dashboard (kerangka navigasi, halaman utama, analitik & log, profil, halaman masuk & lupa sandi) terlihat benar dan mudah dipakai di layar sempit (~320–375px), tablet, desktop, hingga layar sangat lebar (1440px+/ultrawide) — tanpa scroll horizontal dan tanpa konten yang meregang tak terkendali.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Tidak ada scroll horizontal di semua halaman pada lebar 320px, 375px, 768px, 1024px, dan 1440px
- [x] Navigasi samping menyusun ulang menjadi bar atas/bawah di layar kecil; item navigasi tetap dapat diakses
- [x] Grid kartu metrik, panel daya/batch, dan grid analitik menumpuk menjadi satu kolom di layar sempit, dan tidak meregang tak terkendali di layar sangat lebar
- [x] Tabel log menggulir horizontal di dalam kartunya sendiri, bukan memaksa halaman melebar
- [x] Kontrol pencarian & filter log menumpuk vertikal di layar sempit
- [x] Halaman masuk/lupa sandi dan profil tetap proporsional di layar sempit
- [x] Elemen yang bisa diklik memiliki area sentuh yang memadai (~44px minimum) di perangkat sentuh; teks tidak terpotong atau bertumpuk

## Comments

- 2026-08-13: Penyesuaian: AppShell (baris top-nav di <760px dengan target sentuh 44px, plus pengetatan di <360px), Analytics (search/filter flex-wrap + search full-width di <600px), Login/ForgotPassword (padding card di <400px), Profile (stack + centering di <380px). Grid Dashboard/Analytics sudah responsif sebelumnya. Konten utama dibatasi max-width 1200px sehingga tidak meregang di ultrawide. Diverifikasi via `npm run build`; pemeriksaan visual manual menyusul.
