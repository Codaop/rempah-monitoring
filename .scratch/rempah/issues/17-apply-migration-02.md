# 17 — Apply migration 02 ke Supabase

**What to build:** Migration `scripts/migrations/02_alerts_and_batch_logs_constraint.sql` (tabel `alerts` + unique index `batch_logs(batch_id)` + index `sensor_logs(batch_id)`) belum diterapkan ke project Supabase REMPAH. Tanpa ini, Bridge gagal menulis alert over-temperature dan upsert estimasi ke `batch_logs` (`on_conflict="batch_id"` butuh constraint unik).

**Blocked by:** None — can start immediately

**Status:** done

- [x] Terapkan `02_alerts_and_batch_logs_constraint.sql` ke project `qjroojbtquvrdgawxcrw` (SQL Editor di Supabase dashboard, atau `supabase db push`)
- [x] Verifikasi tabel `alerts` ada (SELECT 1 FROM alerts LIMIT 1)
- [x] Verifikasi `batch_logs_batch_id_key` unique index ada (`\d batch_logs` atau query pg_indexes)
- [x] Verifikasi index `sensor_logs(batch_id)` ada

## Comments

- 2026-08-12: Migration diterapkan via MCP sebagai `alerts_table_and_sensor_logs_index`. Dua penyesuaian vs draf awal: (1) unique index `batch_logs_batch_id_key` tidak dibuat — `batch_id` sudah PRIMARY KEY, upsert Bridge (`on_conflict="batch_id"`) sudah terpenuhi; (2) policy INSERT "bridge writes alerts" dihapus — Bridge memakai service_role yang bypass RLS, dan with-check terbuka akan membiarkan operator lain menulis. File repo `scripts/migrations/02_alerts_and_batch_logs_constraint.sql` diperbarui agar konsisten.
- 2026-08-12: Diverifikasi via SQL: kolom `alerts` (id, producer_id, device_id, kind, value, ts) ada, `sensor_logs_batch_id_idx` ada, `batch_logs_pkey` ada.
