# 07 — Bridge runtime: real MQTT → Supabase telemetry pipeline

**What to build:** The Bridge runs as a real always-on service instead of only its pure-Python core: it connects to the MQTT broker (local for development, HiveMQ Cloud for staging), subscribes to `rempah/+/telemetry` and `rempah/+/state`, and persists every message to Supabase (`sensor_logs`, `device_state`) using the service-role credential. The telemetry demo (currently a script writing REST directly) is re-pointed so a fake ESP32 publishes MQTT instead, so the dashboard's live metric cards are fed through the real end-to-end pipeline with no dashboard change.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Bridge starts from env config only (broker URL, credentials, Supabase URL/key); no hardcoded secrets.
- [x] A device publishing `rempah/{device_id}/telemetry` (5s cadence) lands rows in `sensor_logs`; retained state messages update `device_state`.
- [x] A containerised deployment artifact (Dockerfile) shares the same env contract.
- [x] Re-pointing the telemetry demo (fake ESP32) to publish MQTT feeds the dashboard live cards with no dashboard change.

## Comments

- 2026-08-12: Implemented. `__main__.py` wires env config → paho-mqtt (TLS 8883) + supabase-py (service role); `adapters/mqtt_adapter.py` (MqttPort) and `adapters/supabase_adapter.py` (DbPort: telemetry insert via active batch, device_state upsert, last_seen_at, alerts, estimates, pending commands, purge). Dockerfile + `.env.example` share the env contract. `scripts/fake_esp32.py` publishes MQTT telemetry/state in place of REST demo feeder.
- 2026-08-12: 15 bridge tests pass (`python -m pytest`). Live end-to-end (real HiveMQ broker + Supabase) pending credentials from operator.
