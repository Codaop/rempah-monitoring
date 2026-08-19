# 48 — Dokumentasi manajemen akun operator

**What to build:** Panduan ops lengkap untuk admin dalam mengelola akun operator: menambah operator baru (tanpa public sign-up), mengganti password operator secara manual, dan catatan konfigurasi email Supabase untuk fitur reset password. Panduan mencakup langkah lewat dashboard Supabase maupun SQL, sehingga admin tidak perlu menebak-nebak cara kerjanya.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Langkah menambah operator baru terdokumentasi: buat user di Supabase Auth + tautkan ke producer melalui tabel `operators` (via service role)
- [x] Langkah mengganti password operator secara manual terdokumentasi (dashboard Authentication → Users dan/atau SQL)
- [x] Catatan konfigurasi email Supabase terdokumentasi (built-in email service vs SMTP kustom, redirect URL yang harus didaftarkan)
- [x] Seluruh langkah diverifikasi oleh admin dan hasil verifikasi dicatat di Comments

## Comments

- 2026-08-19: Dibuat dari hasil verifikasi database — tabel `operators` tidak punya trigger otomatis dari `auth.users` dan hanya punya policy SELECT, sehingga insert harus via service role. Data saat ini: 1 operator (`admin@gmail.com`) milik producer "Rempah Jaya".
- 2026-08-19: Dokumentasi ditulis di `docs/ops.md` §4b "Manajemen akun operator" (tambah operator, ganti password, syarat email reset, built-in vs custom SMTP). Temuan tambahan dari tiket 47: `admin@gmail.com` ditolak extended email validation (gmail lokal part < 6), jadi panduan menyarankan email ≥ 6 karakter atau nonaktifkan validasi tersebut.
