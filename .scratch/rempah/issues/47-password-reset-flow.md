# 47 — Alur reset password lewat email yang berfungsi penuh

**What to build:** Operator yang lupa password meminta link reset dari halaman login. Email berisi link yang membuka halaman khusus "Atur Password Baru" (bukan diarahkan ke dashboard), tempat operator memasukkan password baru beserta konfirmasinya. Setelah berhasil, operator dapat masuk dengan password baru. Alur ini juga memastikan email reset benar-benar terkirim — termasuk verifikasi konfigurasi email Supabase dan redirect URL yang terdaftar.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Link dari email reset membuka halaman "Atur Password Baru", bukan halaman dashboard
- [ ] Sesi recovery (event `PASSWORD_RECOVERY`) ditangani dengan benar oleh halaman tersebut
- [ ] Form password baru + konfirmasi dengan validasi (kecocokan konfirmasi, aturan panjang) dan umpan balik error yang jelas
- [ ] Setelah berhasil, operator dapat login dengan password baru
- [ ] Permintaan reset mengirim email asli (terverifikasi via log auth / `recovery_sent_at`), dan redirect URL terdaftar di pengaturan auth Supabase
- [ ] Router tidak mengarahkan halaman recovery kembali ke login/dashboard

## Comments

- 2026-08-19: Dibuat dari hasil diagnosis — `recovery_sent_at` masih `null` (belum pernah ada email reset terkirim), redirect `ForgotPassword` menuju dashboard yang tidak menangani event recovery, dan tidak ada form set password baru di aplikasi.
