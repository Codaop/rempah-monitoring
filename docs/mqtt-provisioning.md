# MQTT Provisioning & Canonical Contract

Panduan provisioning device distilasi ke broker MQTT dan kontrak payload untuk tim
firmware ESP32. Broker: HiveMQ Cloud Serverless (ADR 0003).

---

## Model kredensial & topik (keputusan tim, ticket 39)

- **Satu credential MQTT bersama** untuk semua device — dibuat **sekali** di web
  HiveMQ console. Tidak ada username/password per-device.
- **Root topik ditetapkan `rempah/`** — bukan env configurable.
- **Pembeda antar unit**:
  - `device_id` (UUID dari `devices.id` di Supabase) di segmen ke-2 topik;
  - `client_id` MQTT **unik per perangkat**, di-set di **firmware ESP32**
    (mis. `client-<device_id>`) — **bukan** di web HiveMQ console.
    Web HiveMQ hanya dipakai untuk membuat credential bersama sekali.

```
rempah / {device_id} / telemetry|state|command
   │          │                │
 fixed    UUID devices.id     rutekan pesan (fixed)
```

---

## Alur provisioning web-driven

Kartu flash di dashboard adalah **lembar referensi nilai** untuk konfigurasi
awal firmware — **bukan** mekanisme self-provisioning. ESP32 baru tidak punya
firmware, jadi setup pertama selalu dilakukan developer secara manual
(flash via USB/serial). Alurnya:

### 1. Buat akun & credential bersama HiveMQ (sekali)

- [ ] Daftar di [hivemq.com/mqtt-cloud-broker](https://www.hivemq.com/mqtt-cloud-broker/) (Free Serverless)
- [ ] Catat **Cluster URL** (contoh: `abc123.s1.eu.hivemq.cloud`) dan **Port TLS: 8883**
- [ ] Di HiveMQ console → **Access Management** → tambah **satu** credential
      yang dipakai semua device, mis.:
  - Username: `rempah-device`
  - Password: (generate acak, simpan aman)
- [ ] Set credential yang sama di env **dashboard** (`VITE_MQTT_DEVICE_USERNAME` /
      `VITE_MQTT_DEVICE_PASSWORD`) agar kartu flash menampilkannya
- [ ] Buat credential **Bridge** terpisah (username `rempah-bridge`) dan simpan
      di `bridge/.env`:
  ```
  MQTT_BROKER=abc123.s1.eu.hivemq.cloud
  MQTT_PORT=8883
  MQTT_USERNAME=rempah-bridge
  MQTT_PASSWORD=<password>
  ```

### 2. Daftarkan device via web

- [ ] Buka dashboard → **Pengaturan** → **Manajemen Perangkat** →
      **Daftarkan Perangkat Baru**, isi nama (mis. "Boiler Utama")
- [ ] Sistem membuat baris `devices` dengan UUID; **kartu flash** muncul berisi
      semua nilai referensi yang dibutuhkan firmware

### 3. Kartu flash sebagai referensi nilai

Kartu flash menampilkan (dapat dibuka lagi dari daftar perangkat kapan saja):

| Nilai | Contoh |
|---|---|
| Device ID (UUID) | `1a1a0000-0000-4000-8000-000000000001` |
| Topic telemetry | `rempah/1a1a0000-.../telemetry` |
| Topic state | `rempah/1a1a0000-.../state` |
| Topic command | `rempah/1a1a0000-.../command` |
| MQTT username (bersama) | `rempah-device` |
| MQTT password (bersama) | (dari env dashboard) |

### 4. Konfigurasi awal firmware oleh developer (meja kerja, USB/serial)

- [ ] Broker: host dari Cluster URL, port **8883** (TLS)
- [ ] TLS: gunakan Let's Encrypt root CA (`ISRG Root X1`) — tersedia di ESP-IDF
      dan Arduino mbedTLS
- [ ] TLS-SNI: aktifkan dan set ke hostname broker
- [ ] **MQQT client_id unik** per unit, mis. `client-1a1a0000-0000-4000-8000-000000000001`
      — di-set di firmware, **bukan** di web HiveMQ
- [ ] Username/password **bersama** (dari kartu flash)
- [ ] Topic telemetry/state sesuai UUID device (dari kartu flash)
- [ ] Field `ts` di payload — **wajib string ISO 8601 UTC** (lihat bagian
      Canonical Payload), bukan angka/`HHMMSS`. Contoh benar:
      `"ts": "2026-08-12T08:30:00Z"`. Format selain itu membuat data
      ditolak database (bridge akan memakai waktu terimanya sendiri sebagai
      pengganti — data tetap masuk, tapi timestamp jadi kurang akurat)
- [ ] Flash firmware via USB/serial

> **Catatan:** WiFi-AP provisioning (device jadi hotspot untuk di-set ulang tanpa
> re-flash) dicatat sebagai opsi **masa depan** untuk konfigurasi ulang — bukan
> target alur saat ini.

### 5. Verifikasi koneksi

- [ ] Nyalakan device → device connect WiFi + MQTT → publish telemetry
- [ ] Di dashboard, perangkat berubah **Online** (dalam < 60 detik) dan alert
      **"terhubung pertama kali"** muncul — tanda provisioning berhasil end-to-end
- [ ] Cek Bridge log (`python -m rempah_bridge`) — harus muncul `"MQTT connected"`
      dan row baru di `sensor_logs`

### Troubleshooting

- **Device Online tapi tidak ada data / status "menunggu koneksi pertama":**
  cek Bridge log — kalau muncul `date/time field value out of range`,
  `ts` di payload tidak valid (bukan ISO 8601). Perbaiki format `ts` di
  firmware menjadi string ISO 8601 UTC (mis. `2026-08-12T08:30:00Z`).
  Bridge sejak ticket 49 menormalkan `ts` rusak ke waktu terimanya sendiri
  sehingga device tetap tercatat online, tapi timestamp asli device hilang.
- **Device tak dikenal:** bridge mencatat pesan dari `device_id` yang tidak
  terdaftar ke tabel `unknown_messages` dan dashboard menampilkan alert
  "Pesan dari device tak dikenal …" — biasanya UUID di topik salah ketik atau
  device salah flash.
- **Menunggu koneksi pertama > 7 hari:** dashboard menampilkan banner peringatan
  dengan tautan panduan ini; kemungkinan firmware belum dikonfigurasi.

---

## Canonical Payload Examples

Salin verbatim sebagai referensi implementasi firmware.

### Telemetry — `rempah/{device_id}/telemetry`

Dikirim setiap **5 detik**, QoS 1, **bukan retained**.

```json
{
  "ts": "2026-08-12T08:30:00Z",
  "boiler_temp_c": 94.5,
  "gas_mass_kg": 28.6,
  "water_level": 65.2,
  "drip_count": 7,
  "flame_lit": true
}
```

| Field | Type | Keterangan |
|---|---|---|
| `ts` | ISO 8601 UTC | Timestamp dari device (RTC atau NTP) |
| `boiler_temp_c` | number | Suhu boiler dalam °C |
| `gas_mass_kg` | number | Massa/berat gas LPG dari sensor beban (load cell) dalam kg |
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

Root topic **ditetapkan `rempah/`** (keputusan tim, ticket 39). Semua komponen —
bridge subscribe, forward command, fake_esp32, probe — memakai root yang sama.

| Topic | Arah | QoS | Retained |
|---|---|---|---|
| `rempah/{device_id}/telemetry` | Device → Broker | 1 | ✗ |
| `rempah/{device_id}/state` | Device → Broker | 1 | ✓ |
| `rempah/{device_id}/command` | Bridge → Device | 1 | ✗ |

Bridge subscribe ke wildcard: `rempah/+/telemetry` dan `rempah/+/state`.

Struktur wajib 3 level (`rempah/device_id/type`) karena `on_message` di
`__main__.py` meng-parse `topic.split("/")` dan membuang pesan yang bukan
3 bagian; segmen ke-3 harus persis `telemetry` atau `state` agar dirutekan
(selain itu di-drop diam-diam). Segmen ke-2 (device_id) harus cocok dengan
`devices.id` di Supabase — kalau tidak cocok, bridge mencatat pesan sebagai
device tak dikenal (tabel `unknown_messages` + alert di dashboard) alih-alih
memprosesnya.

---

## Struktur topik (cara kerja segmen)

Setiap topic punya 3 segmen, dipisah `/`, masing-masing dengan peran berbeda:

```
rempah / {device_id} / {type}
   │          │            │
 fixed    kunci DB    rutekan pesan
 (rempah) devices.id  (fixed)
```

| # | Segmen | Boleh diganti? | Catatan |
|---|---|---|---|
| 1 | `root` | ❌ Fixed | Ditetapkan `rempah`. Tidak lagi env configurable. |
| 2 | `device_id` | ⚠️ Terikat DB | Harus **persis** `devices.id` di Supabase (tipe UUID, mis. `1a1a0000-0000-4000-8000-000000000001`). Bridge memakainya untuk lookup: `insert_telemetry(device_id)` → `sensor_logs`, `device_state`, dsb. Nama bebas seperti `boiler` TIDAK akan ketemu → dicatat sebagai device tak dikenal. |
| 3 | `type` | ❌ Fixed | Harus `telemetry`, `state`, atau `command`. `on_message` merutekan dari nilai ini; nilai lain di-drop diam-diam. |

### Alur parse di Bridge (kenapa 3 level)

```python
parts = msg.topic.split("/")          # "rempah/1a1a.../telemetry"
if len(parts) != 3: return             # bukan 3 level → dibuang
_, device_id, msg_type = parts         # device_id = segmen 2
if msg_type == "telemetry":
    bridge.handle_telemetry(device_id, payload)   # segmen 2 dipakai utk lookup DB
elif msg_type == "state":
    bridge.handle_state(payload)                  # device_id dibaca dari payload
```

### Nama ramah di topic (opsi lanjutan)

Karena segmen 2 harus UUID, kalau ingin nama ramah (`boiler`) di topic, perlu
sebuah lapisan alias: bridge me-resolve nama → UUID (mis. kolom `slug` di tabel
`devices`, atau tabel pemetaan) sebelum lookup DB. Ini perubahan kode kecil di
bridge — **belum diimplementasikan**. Pilih salah satu:

- **Opsi A (paling sederhana):** pakai UUID langsung di topic.
- **Opsi B:** tambah kolom `slug`/`alias` di `devices`, bridge resolve dulu
  (perlu migrasi kecil + penyesuaian `handle_telemetry`).
