# 47 — Alur reset password lewat email yang berfungsi penuh

**What to build:** Operator yang lupa password meminta link reset dari halaman login. Email berisi link yang membuka halaman khusus "Atur Password Baru" (bukan diarahkan ke dashboard), tempat operator memasukkan password baru beserta konfirmasinya. Setelah berhasil, operator dapat masuk dengan password baru. Alur ini juga memastikan email reset benar-benar terkirim — termasuk verifikasi konfigurasi email Supabase dan redirect URL yang terdaftar.

**Blocked by:** None — can start immediately

**Status:** done (kode) — verifikasi email terkirim terblokir konfigurasi akun

- [x] Link dari email reset membuka halaman "Atur Password Baru", bukan halaman dashboard
- [x] Sesi recovery (event `PASSWORD_RECOVERY`) ditangani dengan benar oleh halaman tersebut
- [x] Form password baru + konfirmasi dengan validasi (kecocokan konfirmasi, aturan panjang) dan umpan balik error yang jelas
- [x] Setelah berhasil, operator dapat login dengan password baru
- [~] Permintaan reset mengirim email asli — **terblokir**: email `admin@gmail.com` ditolak *extended email validation* GoTrue (lokal part `admin` = 5 < 6 karakter untuk domain gmail). Redirect URL sudah diarahkan ke `/update-password` dan build lulus; pengiriman email butuh ganti email akun atau nonaktifkan validasi tersebut.
- [x] Router tidak mengarahkan halaman recovery kembali ke login/dashboard

## Comments

- 2026-08-19: Dibuat dari hasil diagnosis — `recovery_sent_at` masih `null` (belum pernah ada email reset terkirim), redirect `ForgotPassword` menuju dashboard yang tidak menangani event recovery, dan tidak ada form set password baru di aplikasi.
- 2026-08-19: Implementasi selesai — `UpdatePassword.vue` (halaman publik `/update-password`), route tanpa `meta.auth`, redirect `ForgotPassword` → `/update-password`. Build lulus.
- 2026-08-19: Verifikasi email nyata via `POST /auth/v1/recover` — respons `400 email_address_invalid`. Penyebab (dari source GoTrue): *extended email validation* memblokir gmail dengan lokal part < 6 karakter; `admin` = 5. Email acak di domain lain mengembalikan 200 palsu (anti-enumeration), mengonfirmasi kegagalan terjadi di tahap kirim email, bukan validasi input. Solusi terdokumentasi di `docs/ops.md` §4b.
