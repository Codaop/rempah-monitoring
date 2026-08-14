# 27 — Migration: `sensor_logs.batch_id` nullable + purge baris idle

**What to build:** Migration SQL (`scripts/migrations/05_...sql`) yang mengubah `sensor_logs.batch_id` menjadi nullable dan memperluas `purge_old_sensor_logs` di bridge agar baris tanpa batch (idle) yang berumur lebih dari 7 hari ikut dibersihkan. Setelah ini, telemetry dari perangkat bisa disimpan meski tidak ada batch aktif, dan data idle tidak menumpuk selamanya.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `batch_id` pada `sensor_logs` menjadi nullable tanpa kehilangan data existing
- [ ] Baris idle (`batch_id` NULL) berumur >7 hari ikut terpurge oleh retention
- [ ] Migration teruji jalan di project Supabase (tidak error, rollback aman)
