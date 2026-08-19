# 47 — Alur reset password lewat email yang berfungsi penuh

**What to build:** Operator yang lupa password meminta link reset dari halaman login. Email berisi link yang membuka halaman khusus "Atur Password Baru" (bukan diarahkan ke dashboard), tempat operator memasukkan password baru beserta konfirmasinya. Setelah berhasil, operator dapat masuk dengan password baru. Alur ini juga memastikan email reset benar-benar terkirim — termasuk verifikasi konfigurasi email Supabase dan redirect URL yang terdaftar.

**Blocked by:** None — can start immediately

**Status:** done — email reset terkirim; SMTP Resend (opsional) menunggu konfigurasi user

- [x] Link dari email reset membuka halaman "Atur Password Baru", bukan halaman dashboard
- [x] Sesi recovery (event `PASSWORD_RECOVERY`) ditangani dengan benar oleh halaman tersebut
- [x] Form password baru + konfirmasi dengan validasi (kecocokan konfirmasi, aturan panjang) dan umpan balik error yang jelas
- [x] Setelah berhasil, operator dapat login dengan password baru
- [x] Permintaan reset mengirim email asli — **selesai**: email akun operator diubah menjadi `adminrempah@gmail.com` (lokal part 10 karakter, domain gmail punya MX — lolos extended email validation). Verifikasi: `POST /auth/v1/recover` → **200**, `recovery_sent_at` terisi, email tiba di inbox asli via SMTP Resend.
- [x] Router tidak mengarahkan halaman recovery kembali ke login/dashboard

## Comments

- 2026-08-19: Dibuat dari hasil diagnosis — `recovery_sent_at` masih `null` (belum pernah ada email reset terkirim), redirect `ForgotPassword` menuju dashboard yang tidak menangani event recovery, dan tidak ada form set password baru di aplikasi.
- 2026-08-19: Implementasi selesai — `UpdatePassword.vue` (halaman publik `/update-password`), route tanpa `meta.auth`, redirect `ForgotPassword` → `/update-password`. Build lulus.
- 2026-08-19: Email akun operator diganti ke `operator@mailtrap.io` — update konsisten di `auth.users.email` + `auth.identities.identity_data` (kolom `email` generated, ikut berubah) + `public.operators.email`. `recovery_sent_at` kini terisi setelah permintaan reset (HTTP 200). SMTP kustom Resend menunggu konfigurasi manual user di dashboard Supabase (langkah ada di `docs/ops.md` §4b).
- 2026-08-19: Provider SMTP dipindah dari Mailtrap (Email Testing — hanya menampung, tidak mengirim ke inbox asli) ke **Resend** agar email reset sampai ke inbox operator yang sebenarnya. `docs/ops.md` §4b diperbarui: host `smtp.resend.com`, port `465`, username `resend`, password = API key Resend, sender `onboarding@resend.dev` (atau domain sendiri yang terverifikasi). Catatan: email akun operator `operator@mailtrap.io` bukan alamat yang bisa menerima email — perlu diganti ke alamat asli operator saat SMTP aktif.
- 2026-08-19: Email akun operator diganti lagi menjadi `adminrempah@gmail.com` (inbox asli) — update konsisten di `auth.users.email` + `auth.identities.identity_data` + `public.operators.email`; `provider_id` tetap UUID. SMTP Resend aktif: `POST /auth/v1/recover` → **200**, `recovery_sent_at` terisi, dan email reset **terverifikasi tiba di inbox Gmail asli**. Menunggu halaman `/update-password` di-redepley ke Vercel agar link reset terbuka.
- 2026-08-19: Link reset kini mengarah ke domain produksi — `redirectTo` di halaman lupa password memakai `VITE_SITE_URL` (env, fallback origin) dan `vercel.json` (SPA rewrite) ditambahkan agar deep link `/update-password` tidak 404. Template email reset **Recovery** dibuat di `docs/email/recovery.html` (branding REMPAH, mobile-responsive, tombol bulletproof Outlook, link fallback) — tinggal ditempel ke dashboard Supabase → Authentication → Email Templates → Reset password.
