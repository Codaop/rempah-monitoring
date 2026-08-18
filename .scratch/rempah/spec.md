# REMPAH — IoT Cardamom Distillation Monitoring & Control

Status: ready-for-agent

## Problem Statement

Running an LPG-fired cardamom distillation still on a farm today means watching the boiler in person — guessing when the temperature is right, when the flame dies, when the boiler runs dry, and when the run is done. REMPAH replaces this with an IoT system: a single ESP32 unit senses boiler temperature, gas pressure, water level, condensate drip rate, and flame presence, while an operator watches a live, mobile-friendly web dashboard and sends commands (start, stop, refill, cooling, emergency stop) from anywhere. The system must keep operator intent and physical reality in sync — commands must never act on stale device state — and it must scale to multiple machines and concurrent sessions without architectural change.

## Solution

An always-connected telemetry and command pipeline: ESP32 publishes sensor data to a managed MQTT broker; a persistent Python bridge service relays telemetry into Supabase and forwards operator commands back to the device. Command safety is enforced by optimistic concurrency: every command carries the state the operator believes the device is in, and the bridge rejects the command if reality differs, prompting a refresh. An emergency stop always bypasses validation. Operators log in through admin-registered accounts. Each distillation run is recorded as a Batch inside a Monitoring Session, so yield can be compared across runs, machines, and producers.

## User Stories

1. As an operator, I want to see live boiler temperature, so that I can monitor heating progress without standing at the still.
2. As an operator, I want to see live LPG gas pressure, so that I can confirm the burner is supplied.
3. As an operator, I want to see the boiler water level, so that I can prevent the boiler running dry.
4. As an operator, I want to see the condensate drip rate, so that I can judge distillation progress.
5. As an operator, I want to see flame-detection status, so that I can detect an extinguished flame.
6. As an operator, I want to see the cooling-water temperature metric, so that I can gauge condenser effectiveness.
7. As an operator, I want to see the device's current operating mode at all times, so that I know exactly what it is doing now.
8. As an operator, I want all live values to update without manual refresh, so that I can keep watching a long run.
9. As an operator, I want my dashboard to render comfortably on a phone, so that I can monitor from the field.
10. As an operator, I want the dashboard to speak Indonesian, so that labels and actions are natural to the team and farmers.
11. As an operator, I want to create a Monitoring Session and select which devices it covers before it opens, so that I can supervise several machines under one session.
12. As an operator, I want to enter the Charge Mass when a batch starts, so that the target yield and progress can be derived from it.
13. As an operator, I want a Batch to open automatically when a device starts heating and close automatically at completion, so that no manual record-keeping is needed.
14. As an operator, I want to start a distillation run remotely, so that I can begin heating without being at the device.
15. As an operator, I want to stop a distillation run remotely, so that I can end heating on schedule.
16. As an operator, I want to trigger a boiler auto-refill, so that water level is restored without manual topping-up.
17. As an operator, I want to start or stop condenser cooling-water flow, so that I can manage condensation actively.
18. As an operator, I want my command to succeed only when the device state I believe in actually matches reality, so that I never act against stale information.
19. As an operator, when my command's expected state does not match reality, I want to be told and prompted to refresh, so that I do not silently act on outdated beliefs.
20. As an operator, I want an emergency stop that works regardless of current state, so that I can halt the process in any hazard.
21. As an operator, I want to see confirmation that my command was executed, so that I know the device actually acted.
22. As an operator, I want to see a clear marker when a command could not be executed, so that I know the action failed rather than guessing.
23. As an operator, I want to know when the device has gone offline, so that I do not send commands that can never arrive.
24. As an operator, I want alerts on dangerous boiler temperature, so that I can intervene before damage.
25. As an operator, I want alerts when the flame goes out, so that I can re-ignite or stop.
26. As an operator, I want alerts when the boiler water level is critically low, so that a refill or stop happens in time.
27. As an operator, I want to be notified when the distillation end-point is reached, so that I can end the run at peak yield.
28. As an operator, I want to see the estimated yield with progress toward the target, so that I can judge how the run is going.
29. As an operator, I want to see an estimated finish time, so that I can plan around the run's end.
30. As an operator, I want every run recorded as a Batch with its temperature and duration profile and yield, so that I can analyze what produces the best yield.
31. As an operator, I want to compare batches across sessions, machines, and harvests, so that I can tune the process.
32. As an operator, I want to browse the system log (events, sensor readings, values, status), so that I can trace what happened and when.
33. As an operator, I want to search and filter the system log, so that I can find specific events quickly.
34. As an operator, I want to preview and download a PDF report of a batch, so that I can share or archive results.
35. As an admin, I want to register operator accounts with no public sign-up, so that only known operators can watch or control a still.
36. As an operator, I want to log in, so that my commands are attributed to me in the audit trail.
37. As a producer, I want my devices, sessions, batches, and data isolated from other producers, so that multi-tenant scaling is safe from day one.
38. As a system owner, I want each device to authenticate uniquely to the broker, so that a compromised or counterfeit device cannot join the network.
39. As an operator, I want the device to report its state after executing a command and whenever it detects a change itself, so that the cloud's notion of state stays trustworthy.

## Implementation Decisions

### Architecture
- Non-monolithic pipeline: ESP32 → managed MQTT broker → Python Bridge → Supabase → web dashboard; commands flow in reverse; device state changes close the loop via Supabase. The Bridge is the only self-managed runtime component.
- Bridge deployment is Azure for now, migrating to a VPS later; it must stay deployment-agnostic (env-config driven, containerised) so the move is trivial.

### Command safety — Option B (optimistic concurrency)
- Every command payload carries `expected_current_state`; the Bridge compares it against the device's stored state and rejects when they differ, prompting a refresh. No locks or sessions.
- Emergency Stop is exempt from validation and is always forwarded.

### Device State
- A single coarse operating-mode enum is the sole ground truth for validation: `IDLE / PREHEAT / DISTILLING / DRAINING / ERROR / ESTOP`. Per-actuator on/off details are telemetry, not validation state.

### Alerts (hybrid)
- **Device-detected** binary events: flame-out → `ERROR`, low water → `ERROR`, end-point reached. The state message itself is the alert.
- **Bridge-computed** over-temperature: the Bridge raises an alert when `boiler_temp_c` exceeds a configured threshold; this stays tunable without firmware changes.

### Firmware side (contract only — implementation out of scope)
- The ESP32 publishes a **retained** state message to `rempah/{device_id}/state` on every state change and after executing every command:
  `{device_id, mode, cause, command_id?, ts}`
  - `cause`: `command_executed:<command_id>` after an executed command; `command_failed:<command_id>` when a command cannot be executed; `detected` on self-detected transitions (flame-out → ERROR, end-point → completion, low water → ERROR).
- Telemetry cadence is 5 seconds, one row per tick: `{ts, boiler_temp_c, gas_pressure_kpa, water_level, drip_count, flame_lit}` (drip counted continuously, bucketed per tick). The dashboard's cooling-water metric ("Suhu Pendingin Air") reads the same boiler-sensor value per design decision; a physically separate cooling-water reading would need an additional sensor.
- End-point detection runs on-device: the drip-rate logic announces completion to the cloud; the cloud never infers it.
- PID setpoint and the PID loop are fixed in firmware (not dashboard-configurable); adjusting the target mid-run requires a re-flash or the local panel.

### MQTT
- Broker: HiveMQ Cloud Serverless FREE (per ADR 0003).
- Topics: `rempah/{device_id}/telemetry`, `rempah/{device_id}/state` (retained), `rempah/{device_id}/command`. The Bridge subscribes to `rempah/+/telemetry` and `rempah/+/state`.
- Device authentication: per-device username/password over TLS (port 8883) plus a separate credential for the Bridge client. Firmware must support Let's Encrypt certs and TLS-SNI.

### Database (Supabase)
- Multi-tenant with `producer_id` on every table. Core shape:
  - `producers`, `operators` (producer_id, email, password_hash, admin-created; role uniform for now), `devices` (producer_id, name, mqtt_username, mqtt_password, last_seen_at)
  - `sessions` (producer_id, opened_by operator, opened_at, closed_at, notes) + `session_devices` junction (fixed at session open, per ADR 0002)
  - `batches` (session_id, device_id, charge_mass_kg, target_yield_l, started_at, ended_at, status) — boundaries derived from state transitions
  - `sensor_logs` (batch_id, ts, boiler_temp_c, gas_pressure_kpa, water_level, drip_count, flame_lit) — one column per sensor, column-per-sensor so metric graphs need no reshaping
  - `batch_logs` (batch_id, peak_temp, duration, yield, estimated_yield, estimated_finish_at, temperature profile) — yield/ETA are Bridge-computed per telemetry
  - `device_state` (device_id, mode, updated_at) — ground truth for validation
  - `commands` (device_id, action, expected_state nullable, status pending/dispatched/succeeded/failed/rejected, created_by operator, created_at)
- Retention: raw `sensor_logs` live while the batch is active plus a 7-day grace tail, then purged; only `batch_logs` aggregates survive long-term.
- Offline detection: the Bridge derives `last_seen_at` from the telemetry cadence and flags the device offline after 1 minute of silence (~12 missed ticks).
- Auth & authorization: Supabase Auth (email/password, admin-created accounts) + Row-Level Security scoping every dashboard read/write by the operator's `producer_id`. Only the Bridge uses the `service_role` key (bypasses RLS); the dashboard client uses the `anon` key with the logged-in JWT.

### Bridge (Python)
- MQTT via paho-mqtt; Supabase via supabase-py (Realtime for pushes) falling back to Postgres LISTEN/NOTIFY or polling if the Realtime client proves unreliable.
- Responsibilities: persist telemetry and state; validate and forward commands; mark command status; derive offline state; compute estimated yield, estimated finish time, and over-temperature alerts.

### Dashboard
- **Vue 3 + Vite + Apache ECharts.** Static-hosted web client reading live data through Supabase Realtime and issuing commands by inserting rows into `commands`.
- Five screens: `/login`, `/forgot-password`, `/dashboard`, `/analytics`, `/profile`. Indonesian UI copy ("Masuk", "Lupa kata sandi?", "Mulai Batch Baru", "Manajemen Sesi").
- Design reference: the design tokens and components in the team's UI specification (light-grey `#E8ECF0` background, white cards, navy primary `#1C2B3A`, teal accent `#3A7CA5`, red danger `#E53E3E`; 5.1–5.13 component set) — the seam at which dashboard work is verified.
- Dashboard sections: four metric cards (Suhu Boiler, Tekanan Gas, Suhu Pendingin Air, Perkiraan Hasil), power & emergency panel (power toggle + Emergency Stop), batch progress panel (start time, estimated finish, Charge Mass, progress bar), notification log; analytics page with PDF report panel (client-side preview + download) and system log table (CAPTIME / KEJADIAN & SENSOR / NILAI / STATUS) with search and filter; profile page with profile form and session management card. **STATUS LISTRIK panel excluded by design decision.**
- PDF export is **client-side** (browser-generated from batch data) — the lighter technical path chosen for v1.

## Testing Decisions

- **Good test = external behavior at the Bridge seam**, never internals: drive the Bridge with fake broker events and command rows; assert only observable effects (forwarded MQTT commands, Supabase writes, rejected commands, status updates).
- **Module tested:** the Bridge, at its two ports (MQTT and Supabase), behind stubs.
- **Founding suite:** happy-path forward; mismatch rejection (stale expected_state); emergency-stop bypass with no expectation; command-failed status; telemetry persistence; offline detection after 1 minute; over-temperature alert computation; estimated-yield/ETA computation.
- **Prior art:** none — greenfield; this suite establishes the pattern for the repo.

## Out of Scope

- ESP32 firmware implementation, including PID loop internals and the state-machine timing (its MQTT contract is specified here; the device behavior is not).
- Physical sensor calibration and actuator wiring.
- STATUS LISTRIK (power/voltage monitoring) — rejected by design decision.
- Server-side PDF generation (client-side chosen for v1).
- Alert delivery venues beyond the dashboard (SMS/push channels).
- Multi-device orchestration beyond session grouping and per-device authentication.
- Monitoring Session administrative features (editing device selection after open).

## Further Notes

1. Python supabase-py Realtime client reliability to be confirmed at implementation; fallback is LISTEN/NOTIFY or polling.
2. Telemetry reality check: 5s cadence locked but sensor output during the build may tune it; sizing (~17k rows/day per active device) holds either way.
3. Bridge hosting: Azure now, VPS later — deployment-agnostic Bridge keeps this trivial.
4. Cooling-water metric reuses the boiler-sensor reading per design decision; revisit if a physically separate reading is ever wanted.