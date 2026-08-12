# Ops Runbook — REM-PAH

Cara menjalankan komponen dari sesi development saat ini. Teknis dalam bahasa
Inggris; penjelasan dalam Bahasa Indonesia.

## Kredensial & environment contract

- Semua kredensial hidup di luar repo (gitignored): `dashboard/.env` untuk kunci
  client dan file env untuk session development. Tidak ada secret di git.
- Supabase: **anon key** dipakai dashboard client (RLS via JWT operator); key
  **service-role** hanya untuk Bridge/demo feeder (bypass RLS).
- Project ref/URL: lihat `dashboard/.env` (`VITE_SUPABASE_URL`).

## 1. Demo feeder (fake ESP32)

Menghasilkan telemetri live (2 perangkat, cadence 5 detik) ke Supabase via
`service-role` — pengganti sementara path ESP32→MQTT→Bridge sampai pipeline MQTT
real selesai (ticket 07).

```bash
SUPABASE_SERVICE_KEY=<service-role key> \
  setsid nohup python3 scripts/demo_feeder.py </dev/null >/tmp/feeder.log 2>&1 &
```

- Log: `tail -f /tmp/feeder.log`
- Hentikan: `kill $(pgrep -f "demo_feeder[.]py")`
- Cadence: env `FEED_INTERVAL` (detik).

## 2. Realtime smoke test

Memverifikasi path login + Realtime (`postgres_changes`) scoped RLS:

```bash
cd dashboard
SUPABASE_URL=<url> SUPABASE_ANON_KEY=<anon key> \
EMAIL=<operator email> PASSWORD=<operator password> \
node --experimental-websocket scripts/realtime-smoke.mjs
```

Node < 22 butuh flag `--experimental-websocket`; browser tidak (WebSocket native).

## 3. Dashboard

```bash
cd dashboard
npm install --prefer-offline   # lambat di network kecil; prefer-offline membantu
npm run dev                    # dev server
npm run build                  # menghasilkan dist/ statik
```

- Config: `dashboard/.env` → `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
  (gitignored).
- `dist/` bisa diserve oleh Vercel/Netlify/CDN apa pun.

## 4. Database (Supabase, project REM-PAH)

- Schema + RLS: migration `rempah_schema_and_rls` (ticket 01 — done).
- Realtime aktif: `sensor_logs`, `device_state`, `batches`, `commands`.
- Seed demo: producer "Rempah Jaya", operator `admin@gmail.com`, 2 perangkat,
  1 session, 1 batch — hanya untuk demo.
- RLS: operator hanya melihat data `producer_id` miliknya; `service-role` bypass.

## 5. Peta kerja berikutnya

Bridge runtime MQTT, command dispatch + feedback, offline detection, compute,
lifecycle session/batch, PDF batch, provisioning firmware, dan retention adalah
ticket `07–15` di `.scratch/rempah/issues/`. Frontier (bisa mulai sekarang):
ticket `07` (bridge telemetry pipeline) dan `14` (MQTT provisioning + contract).