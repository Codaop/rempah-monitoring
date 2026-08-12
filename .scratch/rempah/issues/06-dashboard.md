# 06 — Web dashboard

Status: in-progress

## Problem

Operators watch live telemetry and send commands from a mobile-friendly, Indonesian-language web dashboard.

## Requirements

- **Vue 3 + Vite + Apache ECharts**, static-hosted (Vercel/Netlify), reading live data via Supabase Realtime and issuing commands by inserting `commands` rows.
- Five screens: `/login`, `/forgot-password`, `/dashboard`, `/analytics`, `/profile`.
- Realtime metric cards with sparklines (Suhu Boiler, Tekanan Gas, Suhu Pendingin Air, Perkiraan Hasil); power & emergency panel (power toggle + Emergency Stop); batch progress panel (start time, estimated finish, Charge Mass, progress bar); notification log (hybrid alerts).
- Analytics: PDF report panel (client-side preview + download) and system log table (CAPTIME / KEJADIAN & SENSOR / NILAI / STATUS) with search and filter.
- Profile: profile form + session management card.
- Device state, offline indicator, command execution/refresh prompts (expected-state mismatch → "refresh" prompt).
- Login via Supabase Auth; RLS-scoped data. Indonesian UI copy ("Masuk", "Lupa kata sandi?", "Mulai Batch Baru", "Manajemen Sesi").
- Design tokens/components per the team's UI specification (light-grey bg `#E8ECF0`, white cards, navy primary `#1C2B3A`, teal accent `#3A7CA5`, red danger `#E53E3E`, radius/spacing set).

## Explicitly excluded

- STATUS LISTRIK (power/voltage) panel — rejected by design decision.

Blocked by: 01, 07

## Comments

- 2026-08-12: Dashboard implemented. Vue 3 + Vite + ECharts app in `dashboard/` with five screens (`/login`, `/forgot-password`, `/dashboard`, `/analytics`, `/profile`), Indonesian UI copy, design tokens (bg `#E8ECF0`, navy `#1C2B3A`, teal `#3A7CA5`, red `#E53E3E`). Realtime metric cards with sparklines, power & emergency panel (writes `commands` rows), batch progress panel, notification log; analytics with client-side PDF report (print-to-PDF) and system log table with search/filter; profile form + session card.
- 2026-08-12: Realtime verified with a smoke test (`dashboard/scripts/realtime-smoke.mjs`): operator login → `postgres_changes` subscription on `sensor_logs` → INSERT event delivered (RLS-scoped). Live demo data from `scripts/demo_feeder.py` (service-role, 2 devices, 5s cadence).
- 2026-08-12: `npm run build` succeeds (`✓ built in 19.11s`); static preview served. Deploy target: user pushes to GitHub then deploys (Vercel deferred).