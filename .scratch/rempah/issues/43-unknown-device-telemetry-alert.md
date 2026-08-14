# 43 — Alert telemetry dari device tak dikenal

**What to build:** Ketika bridge menerima telemetry/state dari `device_id` yang tidak ada di tabel `devices` (mis. ESP32 salah flash atau device_id typo), bridge mencatat kejadian tersebut dan memunculkan alert di dashboard — bukan di-drop diam-diam — supaya kesalahan konfigurasi cepat ketahuan. Ini semakin penting di model kredensial bersama, karena topik `device_id` adalah satu-satunya pembeda antar perangkat.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [x] Bridge mencatat telemetry/state dengan `device_id` tak dikenal tanpa crash dan tanpa drop yang tidak berjejak
- [x] Informasi "pesan dari device tak dikenal <id>" tampil di dashboard
- [x] Perilaku untuk device yang dikenal tidak berubah

## Comments

- 2026-08-14: `alerts` tidak bisa dipakai karena FK `device_id NOT NULL → devices(id)` — dibuat tabel baru `unknown_messages` (device_id text, topic, payload jsonb, ts) + RLS select untuk authenticated. Migrasi diterapkan (scripts/migrations/07).
- 2026-08-14: Gating di `Bridge.handle_telemetry`/`handle_state` (seam yang unit-testable): device tak dikenal → `record_unknown_message` (INSERT + logger.warning) dan return tanpa memproses telemetry/state lebih lanjut. 4 tes unit baru: first contact telemetry/state + unknown device telemetry/state.
- 2026-08-14: Dashboard subscribe INSERT `unknown_messages` → alert warn tag UNKNOWN "Pesan dari device tak dikenal <id> — cek konfigurasi firmware".
