# 48 — Dokumentasi manajemen akun operator

**What to build:** Panduan ops lengkap untuk admin dalam mengelola akun operator: menambah operator baru (tanpa public sign-up), mengganti password operator secara manual, dan catatan konfigurasi email Supabase untuk fitur reset password. Panduan mencakup langkah lewat dashboard Supabase maupun SQL, sehingga admin tidak perlu menebak-nebak cara kerjanya.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Langkah menambah operator baru terdokumentasi: buat user di Supabase Auth + tautkan ke producer melalui tabel `operators` (via service role)
- [ ] Langkah mengganti password operator secara manual terdokumentasi (dashboard Authentication → Users dan/atau SQL)
- [ ] Catatan konfigurasi email Supabase terdokumentasi (built-in email service vs SMTP kustom, redirect URL yang harus didaftarkan)
- [ ] Seluruh langkah diverifikasi oleh admin dan hasil verifikasi dicatat di Comments

## Comments

- 2026-08-19: Dibuat dari hasil verifikasi database — tabel `operators` tidak punya trigger otomatis dari `auth.users` dan hanya punya policy SELECT, sehingga insert harus via service role. Data saat ini: 1 operator (`admin@gmail.com`) milik producer "Rempah Jaya".
