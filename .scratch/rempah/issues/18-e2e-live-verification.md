# 18 — Verifikasi E2E live: Bridge + fake ESP32 + dashboard

**What to build:** Verifikasi end-to-end nyata dari pipeline yang sudah diimplementasikan: Bridge (`python -m rempah_bridge`) berjalan sebagai service, fake ESP32 mempublikasikan MQTT, data mengalir ke Supabase, dan dashboard menampilkan semuanya. Butuh kredensial nyata (HiveMQ Cloud + Supabase service role) yang hanya bisa disediakan human.

**Blocked by:** 17 (schema harus lengkap dulu)

**Status:** ready-for-human

- [x] Isi `bridge/.env` dari `bridge/.env.example` (MQTT_BROKER, MQTT_USERNAME/PASSWORD dari HiveMQ Cloud; SUPABASE_URL + SUPABASE_SERVICE_KEY)
- [x] Jalankan `pip install -e .` di `bridge/` lalu `python -m rempah_bridge`
- [x] Jalankan `python bridge/scripts/fake_esp32.py` (mode IDLE dulu) — cek log Bridge "MQTT connected"
- [x] Verifikasi row masuk ke `sensor_logs` dan `device_state` ter-update (dashboard live cards)
- [x] Test loop command: dashboard → "Mulai Batch Baru" (Buka Sesi + Massa Muatan + Mulai Pemanasan) → Bridge forward command → fake ESP32 merespons → batch auto-open → telemetry mengalir
- [x] Test offline: hentikan fake ESP32 > 60 detik → dashboard menandai perangkat offline
- [x] Test emergency stop → device transisi ke ESTOP, batch close

## Comments

- 2026-08-12: Semua komponen (Bridge, adapters, fake_esp32 dengan command handling, dashboard BatchStarter) sudah diimplementasikan dan lulus test unit (19 passed) + build dashboard.
- 2026-08-12: DB-leg pipeline TERVERIFIKASI via SQL langsung ke database nyata (service role): pending/active batch → telemetry → close → upsert `batch_logs` (`yield_l` + interval + peak_temp) — semua kolom/tip sesuai kode Bridge. Bug yang ditemukan & diperbaiki saat verifikasi: `session_devices` insert tanpa `producer_id` (BatchStarter.vue) dan `yield`→`yield_l`/duration interval (supabase_adapter.py, Analytics.vue) — lihat ticket 19.
- 2026-08-12: ⏳ Yang masih menunggu kredensial human: MQTT leg nyata (HiveMQ Cloud `MQTT_BROKER`/`MQTT_USERNAME`/`MQTT_PASSWORD`) dan `SUPABASE_SERVICE_KEY` di `bridge/.env` — tanpa ini Bridge tidak bisa dijalankan sebagai service (kredensial sengaja tidak pernah disimpan di repo).
- 2026-08-12: 🐛 Perbaikan: bridge tidak pernah memuat `bridge/.env` → `KeyError: 'MQTT_BROKER'` saat `py -m rempah_bridge`. Ditambahkan `python-dotenv>=1.0` di `pyproject.toml` + `load_dotenv(bridge/.env)` (path eksplisit) di `__main__.py`, plus error pesan jelas lewat `_require_env()`. 19 test tetap pass. ✅ LIVE RUN SUKSES: bridge konek ke HiveMQ Cloud, 3 thread jalan, dan memproses command pending POWER_ON device 2b2b0000 → PATCH status done (HTTP 200).
- 2026-08-12: 🐛 Perbaikan serupa di `fake_esp32.py`: tanpa load `.env` ia jatuh ke default `localhost:1883` → `ConnectionRefusedError [WinError 10061]`. Kini load `.env` + fallback kredensial device ke `MQTT_USERNAME/PASSWORD` (demo jalan langsung). ✅ fake ESP32 konek ke HiveMQ Cloud dan publish telemetry tiap 5s. Sekalian: `CallbackAPIVersion.VERSION2` di kedua file untuk hilangkan DeprecationWarning paho. 19 test tetap pass.
- 2026-08-12: 🧹 Cross-check topic root: `MQTT_TOPIC_ROOT` kini konfigurabel (default `rempah`) — semua komponen (bridge subscribe, `_forward` command, fake_esp32, probe) membangun topic dari root yang sama. `bridge/.env` dibersihkan dari duplikat `MQTT_TOPIC_ROOT`. Panduan personalisasi segmen topic ada di `docs/mqtt-provisioning.md` (root bebas via env; device_id harus UUID `devices.id`; segmen ke-3 fixed `telemetry|state|command`).
- 2026-08-12: ✅ E2E LIVE VERIFICATION LENGKAP (otomatis via `bridge/scripts/e2e_live_check.py`): telemetry → `sensor_logs` (3318+ row, `last_seen_at` ter-update), POWER_OFF round-trip → command `succeeded`, batch `4d4d0000` ditutup (`completed`, `batch_logs` = peak 97.99°C / duration 24:35:53 / yield 0.3114 L), EMERGENCY_STOP → command `succeeded` + `device_state=ESTOP`, offline → `last_seen_at` diam setelah device berhenti. 19 unit test tetap pass + `npm run build` sukses.
- 2026-08-12: 🐛 3 bug nyata ditemukan E2E (tidak ketangkap unit test karena DB di-mock): (1) `close_active_batch` pakai sintaks agregat PostgREST yang ditolak (`PGRST123` / `PGRST200`) → dihitung ulang di Python dari rows batch; (2) upsert `batch_logs` (`update_estimate` + `close_active_batch`) tanpa `producer_id` → 400 not-null → kini menyertakan `_resolve_producer(device_id)`; (3) `fake_esp32.py`/probe/pub print karakter non-ASCII (`→`, emoji) → `UnicodeEncodeError` cp1252 membunuh thread paho → diganti ASCII (state publish sempat crash sebelum ack).
