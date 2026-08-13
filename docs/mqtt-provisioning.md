# MQTT Provisioning & Canonical Contract

Checklist dan contoh payload untuk tim firmware ESP32. Broker: HiveMQ Cloud Serverless (ADR 0003).

---

## Checklist Provisioning

### 1. Buat akun HiveMQ Cloud

- [ ] Daftar di [hivemq.com/mqtt-cloud-broker](https://www.hivemq.com/mqtt-cloud-broker/) (Free Serverless)
- [ ] Catat **Cluster URL** (contoh: `abc123.s1.eu.hivemq.cloud`) dan **Port TLS: 8883**

### 2. Buat credential Bridge

- [ ] Di HiveMQ console → **Access Management** → tambah credential:
  - Username: `rempah-bridge`
  - Password: (generate acak, simpan di `.env`)
- [ ] Simpan di `bridge/.env`:
  ```
  MQTT_BROKER=abc123.s1.eu.hivemq.cloud
  MQTT_PORT=8883
  MQTT_USERNAME=rempah-bridge
  MQTT_PASSWORD=<password>
  ```

### 3. Buat credential per-device

Satu credential per ESP32 unit. Jangan berbagi credential antar device.

- [ ] Untuk setiap device, tambah credential di HiveMQ console:
  - Username: `device-<device_id_pendek>` (contoh: `device-1a1a0000`)
  - Password: (generate acak, flash ke firmware)
- [ ] Catat username di kolom `devices.mqtt_username` di Supabase

### 4. Konfigurasi firmware

- [ ] Broker: host dari Cluster URL, port **8883** (TLS)
- [ ] TLS: gunakan Let's Encrypt root CA (`ISRG Root X1`) — tersedia di ESP-IDF dan Arduino mbedTLS
- [ ] TLS-SNI: aktifkan dan set ke hostname broker
- [ ] MQTT client ID unik per device (bisa pakai `device_id`)
- [ ] Username/password per device (dari langkah 3)

### 5. Verifikasi koneksi

- [ ] Gunakan MQTTX (desktop) atau `mosquitto_sub` untuk subscribe ke `rempah/+/telemetry` dan konfirmasi pesan masuk
- [ ] Cek Bridge log (`python -m rempah_bridge`) — harus muncul `"MQTT connected"` dan row baru di `sensor_logs`

---

## Canonical Payload Examples

Salin verbatim sebagai referensi implementasi firmware.

### Telemetry — `rempah/{device_id}/telemetry`

Dikirim setiap **5 detik**, QoS 1, **bukan retained**.

```json
{
  "ts": "2026-08-12T08:30:00Z",
  "boiler_temp_c": 94.5,
  "gas_pressure_kpa": 3.1,
  "water_level": 65.2,
  "drip_count": 7,
  "flame_lit": true
}
```

| Field | Type | Keterangan |
|---|---|---|
| `ts` | ISO 8601 UTC | Timestamp dari device (RTC atau NTP) |
| `boiler_temp_c` | number | Suhu boiler dalam °C |
| `gas_pressure_kpa` | number | Tekanan gas LPG dalam kPa |
| `water_level` | number | Level air boiler (0–100 %) |
| `drip_count` | integer | Jumlah drip yang terhitung dalam interval ini |
| `flame_lit` | boolean | `true` jika nyala api terdeteksi |

### State — `rempah/{device_id}/state`

Dikirim **setelah eksekusi command** dan **setiap perubahan state yang terdeteksi sendiri**. QoS 1, **retained = true**.

#### Setelah command berhasil dieksekusi

```json
{
  "device_id": "1a1a0000-0000-4000-8000-000000000001",
  "mode": "DISTILLING",
  "cause": "command_executed:c9f2a3b1-0000-4000-8000-000000000042",
  "command_id": "c9f2a3b1-0000-4000-8000-000000000042",
  "ts": "2026-08-12T08:30:05Z"
}
```

#### Setelah command gagal dieksekusi (device menolak)

```json
{
  "device_id": "1a1a0000-0000-4000-8000-000000000001",
  "mode": "IDLE",
  "cause": "command_failed:c9f2a3b1-0000-4000-8000-000000000042",
  "command_id": "c9f2a3b1-0000-4000-8000-000000000042",
  "ts": "2026-08-12T08:30:05Z"
}
```

#### Transisi yang terdeteksi sendiri (flame-out, low water, end-point)

```json
{
  "device_id": "1a1a0000-0000-4000-8000-000000000001",
  "mode": "ERROR",
  "cause": "detected",
  "ts": "2026-08-12T09:15:22Z"
}
```

| Field | Type | Keterangan |
|---|---|---|
| `device_id` | UUID string | ID device (sama dengan topik MQTT) |
| `mode` | enum | `IDLE \| PREHEAT \| DISTILLING \| DRAINING \| ERROR \| ESTOP` |
| `cause` | string | `command_executed:<id>` / `command_failed:<id>` / `detected` |
| `command_id` | UUID string (opsional) | Diisi saat cause bukan `detected` |
| `ts` | ISO 8601 UTC | Timestamp dari device |

### Command — `rempah/{device_id}/command`

Dikirim oleh Bridge ke device, QoS 1.

```json
{
  "command_id": "c9f2a3b1-0000-4000-8000-000000000042",
  "action": "POWER_ON"
}
```

| Action | Deskripsi |
|---|---|
| `POWER_ON` | Mulai pemanasan |
| `POWER_OFF` | Hentikan pemanasan |
| `REFILL` | Trigger auto-refill air |
| `COOLING_ON` | Nyalakan pompa pendingin |
| `COOLING_OFF` | Matikan pompa pendingin |
| `EMERGENCY_STOP` | Emergency stop — selalu diforward tanpa validasi state |

---

## Topic Summary

Root topic bersifat konfigurabel lewat env `MQTT_TOPIC_ROOT` (default: `rempah`)
di `bridge/.env`; semua komponen membangun topic dari root yang sama:
`{MQTT_TOPIC_ROOT}/{device_id}/telemetry|state|command`.

| Topic | Arah | QoS | Retained |
|---|---|---|---|
| `{root}/{device_id}/telemetry` | Device → Broker | 1 | ✗ |
| `{root}/{device_id}/state` | Device → Broker | 1 | ✓ |
| `{root}/{device_id}/command` | Bridge → Device | 1 | ✗ |

Bridge subscribe ke wildcard: `{root}/+/telemetry` dan `{root}/+/state`.

Struktur wajib 3 level (`root/device_id/type`) karena `on_message` di
`__main__.py` meng-parse `topic.split("/")` dan membuang pesan yang bukan
3 bagian; segmen ke-3 harus persis `telemetry` atau `state` agar dirutekan
(selain itu di-drop diam-diam). Segmen ke-2 (device_id) harus cocok dengan
`devices.id` di Supabase.

---

## Panduan Personalisasi Topic (cara kerja segmen)

Setiap topic punya 3 segmen, dipisah `/`, masing-masing dengan peran berbeda:

```
{root} / {device_id} / {type}
   │          │            │
 namespace   kunci DB    rutekan pesan
 (bebas)     devices.id  (fixed)
```

| # | Segmen | Boleh diganti? | Catatan |
|---|---|---|---|
| 1 | `root` | ✅ Bebas | Via env `MQTT_TOPIC_ROOT` di `bridge/.env`. Contoh: `rempah`, `bayunyoba`, `pabrik1`. Semua komponen otomatis ikut — tidak perlu edit kode. |
| 2 | `device_id` | ⚠️ Terikat DB | Harus **persis** `devices.id` di Supabase (tipe UUID, mis. `1a1a0000-0000-4000-8000-000000000001`). Bridge memakainya untuk lookup: `insert_telemetry(device_id)` → `sensor_logs`, `device_state`, dsb. Nama bebas seperti `boiler` TIDAK akan ketemu → data tidak masuk DB. |
| 3 | `type` | ❌ Fixed | Harus `telemetry`, `state`, atau `command`. `on_message` merutekan dari nilai ini; nilai lain di-drop diam-diam tanpa error. |

### Alur parse di Bridge (kenapa 3 level)

```python
parts = msg.topic.split("/")          # "bayunyoba/1a1a.../telemetry"
if len(parts) != 3: return             # bukan 3 level → dibuang
_, device_id, msg_type = parts         # device_id = segmen 2
if msg_type == "telemetry":
    bridge.handle_telemetry(device_id, payload)   # segmen 2 dipakai utk lookup DB
elif msg_type == "state":
    bridge.handle_state(payload)                  # device_id dibaca dari payload
```

### Langkah personalisasi yang benar

1. **Tentukan root** → set `MQTT_TOPIC_ROOT=bayunyoba` di `bridge/.env`.
2. **Daftarkan device asli di Supabase** — id-nya UUID (boleh dibuat manual
   seperti seed, atau `gen_random_uuid()`), lalu pakai UUID itu di segmen 2:
   ```sql
   insert into public.devices (id, producer_id, name)
   values ('a1b2c3d4-...', '0d0d0000-0000-4000-8000-000000000001', 'Boiler Utama');
   ```
   Topic jadi: `bayunyoba/a1b2c3d4-.../telemetry`.
3. **Jaga segmen 3 tetap `telemetry|state|command`** — firmware/publisher harus
   memakai nama ini. Kalau device asli terlanjur pakai nama lain (mis. `data`),
   tambahkan alias routing di `on_message` (`data` → treat sebagai telemetry).

### Opsi lanjutan: nama ramah di topic (mis. `bayunyoba/boiler/telemetry`)

Karena segmen 2 harus UUID, kalau ingin nama ramah (`boiler`) di topic, perlu
sebuah lapisan alias: bridge me-resolve nama → UUID (mis. kolom `slug` di tabel
`devices`, atau tabel pemetaan) sebelum lookup DB. Ini perubahan kode kecil di
bridge — belum diimplementasikan. Pilih salah satu:

- **Opsi A (paling sederhana):** pakai UUID langsung di topic.
- **Opsi B:** tambah kolom `slug`/`alias` di `devices`, bridge resolve dulu
  (perlu migrasi kecil + penyesuaian `handle_telemetry`).
