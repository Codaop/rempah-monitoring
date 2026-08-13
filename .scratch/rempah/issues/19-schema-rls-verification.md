# 19 — Verifikasi skema & RLS: session_devices insert + kolom batch_logs

**What to build:** Dua asumsi skema yang belum terverifikasi terhadap database nyata, keduanya butuh akses Supabase dashboard. Jika tidak sesuai, ada penyesuaian kecil di kode Bridge/dashboard.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Cek RLS policy `session_devices`: tabel junction ini tidak punya kolom `producer_id` (per kontrak), jadi policy insert harus mengizinkan operator menyisipkan `(session_id, device_id)` — uji dengan insert dari dashboard (flow "Buka Sesi" di BatchStarter)
- [x] Jika insert ditolak: tambahkan policy RLS yang sesuai, atau tambahkan `producer_id` ke insert (dengan penyesuaian kode `BatchStarter.vue`)
- [x] Verifikasi kolom `batch_logs`: pastikan kolom `yield`, `duration`, `peak_temp`, `estimated_yield`, `estimated_finish_at` ada dengan tipe yang bisa menerima angka (`yield` adalah kata reserved SQL — cek PostgREST menerimanya)
- [x] Jika kolom bernama berbeda (mis. `yield_l`): sesuaikan `close_active_batch` di `bridge/rempah_bridge/adapters/supabase_adapter.py`

## Comments

- 2026-08-12: Hasil verifikasi schema nyata: `session_devices` **MEMILIKI** kolom `producer_id` (NOT NULL) dengan policy insert `producer_id = operator_producer_id()` — jadi insert dashboard TANPA producer_id ditolak. Bug nyata ditemukan dan diperbaiki: `BatchStarter.vue` kini meng-insert `{session_id, device_id, producer_id}`.
- 2026-08-12: `batch_logs` menggunakan kolom **`yield_l`** (bukan `yield`) dan **`duration` bertipe `interval`** (bukan detik). Bug nyata ditemukan dan diperbaiki di `close_active_batch` (upsert `yield_l` + duration ISO-8601 `PT{n}S`) dan `Analytics.vue` (`log.yield_l`). Simulasi DB-leg lulus: telemetry → close batch → upsert `batch_logs` (peak_temp, duration 01:00:00, yield_l 0.02) → verifikasi → cleanup.
- 2026-08-12: Verifikasi insert RLS penuh sebagai operator (via JWT) belum dijalankan — butuh kredensial login; policy dan kode kini konsisten.
- 2026-08-12: ⏳ Perbaikan Security Advisor disiapkan di `scripts/migrations/03_revoke_security_definer_execute.sql` (belum di-apply — MCP Supabase drop `Unauthorized` saat mau dijalankan): cabut EXECUTE `rls_auto_enable()` dari public/anon/authenticated/service_role, cabut grant PUBLIC `operator_producer_id()` (anon/authenticated TETAP — dipakai policy RLS), dan set default privileges agar fungsi baru tidak otomatis dapat EXECUTE. Sisa lint yang tetap sengaja dipertahankan: `operator_producer_id()` callable anon/authenticated (dokumentasi Supabase mengecualikan fungsi yang dipakai policy RLS; panggilan aman — anon dapat NULL, authenticated hanya producer_id sendiri).
- 2026-08-13: ✅ Migration 03 DI-APPLY (`revoke_security_definer_execute`, versi `20260812172945`) setelah MCP pulih. Verifikasi grants: `rls_auto_enable()` kini hanya postgres/supabase_admin (hilang dari `/rest/v1/rpc`), `operator_producer_id()` tetap executable oleh anon/authenticated (dipakai ~35 policy RLS) — lint 0028/0029 untuk `rls_auto_enable` bersih. Sisa lint 0028/0029 hanya `operator_producer_id` (sengaja, terdokumentasi). Lint baru terdeteksi: `auth_leaked_password_protection` (proteksi password bocor HaveIBeenPwned nonaktif — pengaturan Auth di dashboard, hanya tersedia Pro Plan+; bukan bagian migration, butuh keputusan human).
