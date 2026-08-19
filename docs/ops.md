# Ops Runbook — REMPAH

Cara menjalankan komponen dari sesi development saat ini. Teknis dalam bahasa
Inggris; penjelasan dalam Bahasa Indonesia.

## Interpreter & environment contract

- **Interpreter Python yang benar** untuk semua script bridge: full path ke
  `C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe`.
  Jangan pakai `python` polos dari PATH (`/c/Python314/python`) — ia **tidak**
  punya `dotenv` dan `paho-mqtt`, dan akan gagal dengan
  `ModuleNotFoundError: No module named 'dotenv'`.
- Semua kredensial hidup di luar repo (gitignored): `bridge/.env` untuk
  kredensial MQTT + Supabase service-role, `dashboard/.env` untuk kunci client.
  Tidak ada secret di git.
- `bridge/.env` (wajib untuk bridge & fake ESP; otomatis dimuat oleh script):
  `MQTT_BROKER`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`,
  `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`; opsional `MQTT_TOPIC_ROOT`
  (default `rempah`).
- `dashboard/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- Supabase: **anon key** dipakai dashboard client (RLS via JWT operator); key
  **service-role** hanya untuk Bridge/fake ESP (bypass RLS).
- Project ref/URL: lihat `bridge/.env` (`SUPABASE_URL`).

## 0. Workflow ringkas (3 terminal)

```bash
# Terminal A — Bridge (harus jalan duluan, service)
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m rempah_bridge

# Terminal B — Fake ESP32 (simulasi device, publish telemetry)
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py

# Terminal C — Dashboard (dev server, hot-reload)
cd dashboard
npm run dev
```

Buka `http://localhost:5173`, login sebagai operator, dan dashboard akan
menerima data realtime tiap ~2 detik.

## 0a. START & STOP — ringkasan cepat

Acuan harian untuk memulai dan menghentikan layanan.

### Mulai semua layanan (3 terminal)

Terminal A:
```bash
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m rempah_bridge
```

Terminal B:
```bash
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py
```

Terminal C:
```bash
cd dashboard
npm run dev
```

Buka http://localhost:5173, login sebagai operator.

### Hentikan semua sekaligus

```powershell
Stop-Process -Name python -Force
```
⚠️ Menghentikan **semua** proses Python — pastikan tidak ada script lain yang berjalan.

### Hentikan per-layanan

| Tindakan | Perintah |
| --- | --- |
| Cek proses jalan | `Get-CimInstance Win32_Process \| Where-Object { $_.CommandLine -like '*rempah*' }` |
| Stop bridge | `Stop-Process -Id <PID> -Force` (ganti PID dari kolom ProcessId) |
| Stop fake ESP | Sama seperti bridge, filter command line berisi `fake_esp` |
| Stop dashboard | Tekan `Ctrl+C` di terminal dev server |

Lihat detail lengkap:
• [Bridge — §1 →](#1-bridge-service-mqtt--supabase)
• [Fake ESP32 — §2 →](#2-fake-esp32-device-simulasi)
• [Dashboard — §3 →](#3-dashboard)

## 1. Bridge (service MQTT → Supabase)

Menjalankan pipeline telemetry: subscribe `rempah/+/telemetry` & `rempah/+/state`
dari broker, insert ke `sensor_logs`/`device_state`, forward command, deteksi
offline, purge retention.

```bash
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m rempah_bridge
```

- Baca kredensial dari `bridge/.env`; gagal start bila ada var wajib kosong.
- 3 thread latar: cmd-poll (2s), offline-check (30s), purge (harian) — lihat
  `rempah_bridge/__main__.py`.

### STOP — hentikan bridge

```bash
# Opsi A: tekan Ctrl+C di terminal bridge
# Opsi B: cari PID lalu stop
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*rempah_bridge*' }" | Select-Object ProcessId, CommandLine
powershell -Command "Stop-Process -Id <PID> -Force"
```

## 2. Fake ESP32 (device simulasi)

Menggantikan `scripts/demo_feeder.py` (sudah tidak dipakai — pipeline kini
lewat MQTT sungguhan). Mempublish telemetry ke
`rempah/{FAKE_DEVICE_ID}/telemetry` dengan cadence default **2 detik**, plus
state retained di `rempah/{FAKE_DEVICE_ID}/state`. Otomatis memuat `bridge/.env`
(kredensial broker & topik root).

```bash
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py
```

- Log telemetry tampil di terminal tiap cadence.
- Env yang bisa di-override:
  - `FEED_INTERVAL` — cadence detik (default `2`).
  - `FAKE_DEVICE_ID` — UUID device (default
    `1a1a0000-0000-4000-8000-000000000001`).
  - `FAKE_DEVICE_MODE` — mode state awal (default `DISTILLING`).
  - `FAKE_DEVICE_USERNAME` / `FAKE_DEVICE_PASSWORD` — fallback ke
    `MQTT_USERNAME`/`MQTT_PASSWORD` dari `bridge/.env`.
- Contoh interval 1 detik:
  ```bash
  FEED_INTERVAL=1 "C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py
  ```
- Contoh device kedua (UUID berbeda, mode IDLE):
  ```bash
  FAKE_DEVICE_ID=4d4d0000-0000-4000-8000-000000000002 \
  FAKE_DEVICE_MODE=IDLE \
  "C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py
  ```
  Pastikan device ID sudah terdaftar di tabel `devices`, kalau tidak bridge
  mencatatnya sebagai unknown device (ticket 43).

### Restart (mis. ganti interval)

```bash
# 1. Hentikan fake ESP (ganti PID sesuai hasil cek)
powershell -Command "Get-CimInstance Win32_Process -Filter \"name like '%python%'\" | Select-Object ProcessId,CommandLine | Format-List"
powershell -Command "Stop-Process -Id <PID> -Force"

# 2. Pastikan bridge masih hidup (jangan di-stop), lalu jalankan ulang fake ESP
powershell -Command "Get-CimInstance Win32_Process -Filter \"name like '%python%'\" | Select-Object ProcessId,CommandLine | Format-List"
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py
```

### Detached background (tetap jalan walau terminal ditutup)

```powershell
Start-Process -FilePath 'C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe' `
  -ArgumentList 'scripts/fake_esp32.py' `
  -WorkingDirectory 'C:\Users\MSA-DESKTOP\Desktop\rempah-monitoring\bridge' `
  -WindowStyle Hidden
```

## 2b. Verifikasi delay realtime (dashboard ↔ broker)

Jika data di broker cepat tapi dashboard lambat: subscription Realtime
(`postgres_changes`) dashboard bisa mati bila ada binding ke tabel yang tidak
ada di publikasi `supabase_realtime` — channel ikut ditutup server dan
dashboard jatuh ke polling fallback 30 detik. Pastikan tabel yang dipakai
dashboard (termasuk `unknown_messages`, `devices`, `batch_logs`) ada di
publikasi:

```sql
select schemaname, tablename from pg_publication_tables
where pubname = 'supabase_realtime';
```

## 2c. Realtime smoke test (jalur browser: anon + JWT operator)

Memverifikasi path login + Realtime (`postgres_changes`) scoped RLS persis
seperti browser:

```bash
cd dashboard
SUPABASE_URL=<url> SUPABASE_ANON_KEY=<anon key> \
EMAIL=<operator email> PASSWORD=<operator password> \
node scripts/realtime-smoke.mjs
```

Node < 22 butuh flag `--experimental-websocket`; browser tidak (WebSocket native).

## 2d. MQTT topic probe (sudah terhubung ke broker belum?)

Memverifikasi koneksi MQTT dan trafik topic `rempah/#` pakai kredensial yang
sama dengan `bridge/.env` (otomatis dimuat):

```bash
python bridge/scripts/mqtt_probe.py              # listen 15 detik lalu exit
python bridge/scripts/mqtt_probe.py --watch       # listen terus (Ctrl+C)
python bridge/scripts/mqtt_probe.py --seconds 30
```

- Output `✅ CONNECTED` = broker terjangkau dan kredensial diterima.
- Pesan `rempah/<id>/state` (retained) langsung muncul saat subscribe = topic
  pernah dipublish; pesan `telemetry` muncul bila `fake_esp32.py` berjalan.
- Exit code 1 tanpa pesan = koneksi OK tapi tidak ada trafik; jalankan
  `fake_esp32.py` lalu ulangi. Exit code 2 = gagal konek/refused.

**Test topic sendiri (publish → diterima?)** — dua terminal:

```bash
# Terminal 1 — listen di topic kamu
python bridge/scripts/mqtt_probe.py --topic 'topik-ku/+/data' --watch

# Terminal 2 — publish satu pesan uji (PUBACK = broker menerima)
python bridge/scripts/mqtt_pub.py --topic 'topik-ku/device1/data' --message '{"temp": 95.2}'
# atau berulang tiap 5 detik:
python bridge/scripts/mqtt_pub.py --topic 'topik-ku/device1/data' --message '{"temp": 95.2}' --loop 5
```

- Pesan muncul di Terminal 1 = data dari publish benar-benar sampai di topic.
  `--retain` membuat pesan tersimpan di broker dan langsung diterima subscriber
  baru. Catatan: probe/pub hanyalah alat uji pasif — bridge hanya menelan topic
  `rempah/+/telemetry` & `rempah/+/state` (kontrak ticket 14 & 39); root topic
  ditetapkan `rempah/` — device asli harus memakai UUID `devices.id` di segmen
  topic dan `client_id` unik di firmware (lihat `docs/mqtt-provisioning.md`).

## 2e. E2E live check (otomatis)

Menjalankan bridge + fake ESP32 nyata dan memverifikasi seluruh pipeline sampai
Supabase: telemetry masuk, command round-trip, batch close, offline detection.

```bash
cd bridge
"C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/e2e_live_check.py
```

- **Jangan** dijalankan bersamaan dengan instance bridge/fake_esp32 lain
  (duplikat `client_id` MQTT).
- Output `[PASS]/[FAIL]` per fase; exit code non-zero bila ada fase gagal.

### STOP — hentikan fake ESP32

```bash
# Opsi A: tekan Ctrl+C di terminal fake ESP
# Opsi B: cari PID lalu stop
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*fake_esp*' }"
powershell -Command "Stop-Process -Id <PID> -Force"
```

> 💡 Menghentikan fake ESP32 **tidak** menghapus data yang sudah masuk ke Supabase.
> Data tetap ada di dashboard — kamu hanya berhenti mengirim data baru dari simulasi.

### Restart (mis. ganti interval)

```bash
# 1. Hentikan fake ESP lama
powershell -Command "Stop-Process -Id <PID> -Force"
# 2. Jalankan ulang dengan env baru
cd bridge
FEED_INTERVAL=1 "C:\Users\MSA-DESKTOP\AppData\Local\Python\pythoncore-3.14-64\python.exe" scripts/fake_esp32.py
```

---

## 3. Dashboard

```bash
cd dashboard
npm install --prefer-offline   # lambat di network kecil; prefer-offline membantu
npm run dev                    # dev server (hot-reload di localhost:5173)
npm run build                  # menghasilkan dist/ statik
```

- Config: `dashboard/.env` → `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
  (gitignored).
- `dist/` bisa diserve oleh Vercel/Netlify/CDN apa pun.

### STOP — hentikan dashboard

Tekan `Ctrl+C` di terminal dev server. Untuk paksa mati bila stuck:

```bash
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*vite*' -or $_.CommandLine -like '*node*' }" | Select-Object ProcessId, CommandLine
powershell -Command "Stop-Process -Id <PID> -Force"
```

## 4. Database (Supabase, project REMPAH)

- Schema + RLS: migration `rempah_schema_and_rls` (ticket 01 — done).
- Realtime aktif: `sensor_logs`, `device_state`, `batches`, `commands`, plus
  `unknown_messages`, `devices`, `batch_logs` (migration
  `add_missing_tables_to_realtime_publication` — tanpanya channel realtime
  dashboard mati dan fallback polling 30 detik yang dipakai).
- Seed demo: producer "Rempah Jaya", operator `admin@gmail.com`, 2 perangkat,
  1 session, 1 batch — hanya untuk demo.
- RLS: operator hanya melihat data `producer_id` miliknya; `service-role` bypass.

## 4b. Manajemen akun operator

Semua operasi di bawah butuh akses **Supabase Dashboard** (SQL Editor berjalan
sebagai `postgres`/service role, jadi melewati RLS). Tabel `operators` hanya
punya policy `SELECT` untuk JWT operator dan **tidak ada trigger** yang membuat
baris `operators` dari `auth.users` — sehingga menambah operator = **2 langkah
manual**.

### Tambah operator baru

1. **Buat user auth** — Dashboard → Authentication → Users → **Add user**,
   isi email + password. Catat UUID user (kolom ID) setelah dibuat.
2. **Tautkan ke producer** — Dashboard → SQL Editor, jalankan (ganti nilai
   `<UUID>` dan `<producer-id>`):

   ```sql
   insert into operators (id, producer_id, email, role)
   values (
     '<UUID-auth-user>'::uuid,
     '<producer-id>'::uuid,   -- mis. 0d0d0000-0000-4000-8000-000000000001
     'nama@email.com',
     'operator'
   );
   ```

   Kolom `id` **wajib sama** dengan `auth.users.id` (PK operator = id user
   auth). Email di kolom `operators.email` sebaiknya sama dengan email login.

Cara alternatif via Management API / admin client: `supabase.auth.admin
.createUser(...)` lalu insert `operators` dengan service role — hasil akhir
sama (user auth + baris operators).

### Ganti password operator secara manual

- **Dashboard** — Authentication → Users → pilih user → ⋯ → **Reset
  password** (mengirim email reset ke user) atau **Update user** (set
  password baru langsung).
- **SQL Editor** (admin, langsung tanpa email):
  ```sql
  update auth.users
  set encrypted_password = crypt('password-baru-min-8-karakter', gen_salt('bf'))
  where id = '<UUID-auth-user>'::uuid;
  ```

### Fitur lupa password — persyaratan agar email terkirim

Kode alur reset sudah lengkap di aplikasi (halaman `ForgotPassword` → email →
halaman publik `UpdatePassword`). Agar email benar-benar terkirim, dua hal ini
harus dipenuhi di dashboard:

1. **Redirect URL terdaftar** — Dashboard → Authentication → URL
   Configuration → **Redirect URLs** harus memuat alamat halaman
   `update-password` aplikasi (mis. `https://<domain>/update-password`),
   plus `http://localhost:5173/update-password` untuk dev. Tanpa ini link di
   email ditolak.
2. **Email penerima lolos validasi Supabase** — GoTrue versi terbaru punya
   *extended email validation* yang memblokir alamat berisiko bounce.
   Kasus nyata terverifikasi di project ini:
   - `admin@gmail.com` **ditolak** dengan error `email_address_invalid`
     karena GoTrue memblokir alamat gmail dengan lokal part < 6 karakter
     (`admin` = 5 karakter).
   - **Solusi**: gunakan email dengan lokal part ≥ 6 karakter (mis.
     `admin1@gmail.com`), atau nonaktifkan extended email validation di
     pengaturan auth bila tersedia. Email di `auth.users` dan
     `operators.email` harus diubah bersamaan.
   - Verifikasi cepat: `select recovery_sent_at from auth.users` — terisi
     berarti email reset terkirim.

### Catatan pengiriman email (built-in vs SMTP kustom)

- **Built-in email service** (default, tanpa SMTP kustom) hanya mengirim ke
  alamat anggota tim proyek; selain itu gagal dengan *email not
  authorized*. Rate limit rendah dan availability best-effort — cukup untuk
dev, tidak untuk produksi.
- Untuk produksi: Dashboard → Authentication → SMTP Settings → pasang
  **custom SMTP** (Resend/SES/Postmark/SendGrid). Setelah itu email dapat
  dikirim ke alamat mana pun, dengan rate limit awal 30/jam yang bisa
  dinaikkan di Rate Limits.

## 5. Peta kerja berikutnya

Bridge runtime MQTT, command dispatch + feedback, offline detection, compute,
lifecycle session/batch, PDF batch, provisioning firmware, dan retention adalah
ticket `07–15` di `.scratch/rempah/issues/`. Frontier (bisa mulai sekarang):
ticket `07` (bridge telemetry pipeline) dan `14` (MQTT provisioning + contract).
