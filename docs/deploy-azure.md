# Deploy Bridge ke Azure — Panduan

Bridge adalah **daemon Python** (bukan web server) yang menjalankan:
- subscribe MQTT (`rempah/+/telemetry` & `rempah/+/state`)
- polling command dari Supabase tiap 2 detik
- `client.loop_forever()` — berjalan terus-menerus

Karena itu target deployment yang cocok adalah **Azure Container Apps** (rekomendasi)
atau **Azure Container Instances** — bukan App Service web biasa.

---

## 0. Prasyarat

| Kebutuhan | Status di mesinmu |
|---|---|
| Docker | ✅ v29.4.1 terpasang |
| Azure CLI (`az`) | ❌ belum terpasang — install dulu |
| Akun Azure | perlu (trial $200 gratis cukup) |

### Install Azure CLI (Windows)

```powershell
# Opsi 1 — winget (paling cepat)
winget install Microsoft.AzureCLI

# Opsi 2 — PowerShell script installer
Invoke-WebRequest -Uri https://aka.ms/InstallAzureCli -OutFile .\InstallAzureCLI.ps1
.\InstallAzureCLI.ps1
```

Setelah install, buka terminal baru lalu verifikasi:

```powershell
az version
az login   # buka browser, login akun Azure
```

---

## 1. Opsi deploy: Container Apps (rekomendasi) vs Container Instances

| | **Container Apps** ✅ | **Container Instances** |
|---|---|---|
| Manajemen | Managed environment (auto scale, revisi, secrets) | Single container, manual |
| Restart policy | Otomatis (health check) | `--restart-policy Always` |
| Secrets | Integration dgn Key Vault, env via `--env-vars` | Env via `--environment-variables` |
| Biaya | Berbasis penggunaan, bisa scale-to-zero | Per detik berjalan |
| Cocok untuk | Produksi / demo panjang | Uji coba cepat |

Keduanya butuh **Azure Container Registry (ACR)** atau image publik. Panduan ini
memakai **ACR + Container Apps**.

---

## 2. Build & push image ke Azure Container Registry

```bash
# 1. Buat resource group (sekali)
az group create --name rempah-rg --location southeastasia

# 2. Buat container registry (sekali)
az acr create --resource-group rempah-rg --name rempahacr --sku Basic --admin-enabled true

# 3. Login ke ACR
az acr login --name rempahacr

# 4. Build image bridge
cd bridge
docker build -t rempahacr.azurecr.io/rempah-bridge:latest .

# 5. Push ke ACR
docker push rempahacr.azurecr.io/rempah-bridge:latest
```

---

## 3. Deploy ke Azure Container Apps

```bash
# 1. Buat Container Apps environment (sekali)
az containerapp env create \
  --name rempah-env \
  --resource-group rempah-rg \
  --location southeastasia

# 2. Deploy bridge
az containerapp create \
  --name rempah-bridge \
  --resource-group rempah-rg \
  --environment rempah-env \
  --image rempahacr.azurecr.io/rempah-bridge:latest \
  --registry-server rempahacr.azurecr.io \
  --registry-username rempahacr \
  --registry-password "$(az acr credential show --name rempahacr --query 'passwords[0].value' -o tsv)" \
  --env-vars \
    MQTT_BROKER="<broker-host>" \
    MQTT_PORT="8883" \
    MQTT_USERNAME="rempah-bridge" \
    MQTT_PASSWORD="<bridge-mqtt-password>" \
    SUPABASE_URL="<supabase-url>" \
    SUPABASE_SERVICE_KEY="<service-role-key>" \
  --min-replicas 1 \
  --max-replicas 1
```

> ⚠️ **Penting**: set `--min-replicas 1 --max-replicas 1` — bridge adalah daemon
> yang harus selalu jalan. Jangan aktifkan scale-to-zero, karena bridge yang mati
> berarti tidak ada data yang masuk ke database.

#### PowerShell (Windows) — satu baris

Dokumen ini memakai gaya bash (`\` untuk lanjut baris). Di PowerShell, `\`
bukan karakter lanjut baris (yang benar adalah backtick `` ` ``), jadi salin
perintah sebagai **satu baris utuh**:

```powershell
az containerapp env create --name rempah-env --resource-group rempah-rg --location southeastasia
```

```powershell
az containerapp create --name rempah-bridge --resource-group rempah-rg --environment rempah-env --image rempahacr.azurecr.io/rempah-bridge:latest --registry-server rempahacr.azurecr.io --registry-username rempahacr --registry-password "$(az acr credential show --name rempahacr --query 'passwords[0].value' -o tsv)" --env-vars MQTT_BROKER="<broker-host>" MQTT_PORT="8883" MQTT_USERNAME="rempah-bridge" MQTT_PASSWORD="<bridge-mqtt-password>" SUPABASE_URL="<supabase-url>" SUPABASE_SERVICE_KEY="<service-role-key>" --min-replicas 1 --max-replicas 1
```

Ganti `<broker-host>`, `<bridge-mqtt-password>`, `<supabase-url>`, dan
`<service-role-key>` dengan nilai asli sebelum menjalankan.

### Update env var setelah deploy

```bash
az containerapp update \
  --name rempah-bridge \
  --resource-group rempah-rg \
  --set-env-vars MQTT_PASSWORD="<new-password>"
```

### Update image ke versi baru

```bash
az containerapp update \
  --name rempah-bridge \
  --resource-group rempah-rg \
  --image rempahacr.azurecr.io/rempah-bridge:latest
```

---

## 4. Verifikasi bridge berjalan

```bash
# Lihat status container
az containerapp show --name rempah-bridge --resource-group rempah-rg \
  --query 'properties.runningStatus'

# Lihat log realtime
az containerapp logs show --name rempah-bridge --resource-group rempah-rg

# Lihat log dari container yang sedang berjalan
az containerapp logs show --name rempah-bridge --resource-group rempah-rg --type console
```

Log yang sehat harus menunjukkan:

```
MQTT connected — subscribing to telemetry and state topics
cmd-poll started (2.0s interval)
offline-check started (30.0s interval)
purge started (86400s interval)
```

---

## 5. Menghubungkan dengan Supabase & HiveMQ

Bridge di Azure terhubung ke:

1. **HiveMQ** — pakai kredensial `rempah-bridge` (bukan `rempah-device`). Pastikan
   username `rempah-bridge` punya akses subscribe + publish di HiveMQ console.
2. **Supabase** — pakai **service-role key** (bukan anon key). Key ini bypass RLS,
   jadi jangan pernah bocor ke browser. Aman disimpan di env var Container Apps.

**Firewall / network:**
- HiveMQ Cloud Serverless: tidak ada IP allowlist — koneksi dari Azure OK.
- Supabase: kalau project punya IP restriction, tambahkan IP egress Container Apps
  (bisa dilihat di portal atau `az containerapp show ... --query 'properties.outboundIpAddresses'`).

---

## 6. Troubleshooting umum

| Gejala | Kemungkinan penyebab | Solusi |
|---|---|---|
| `MQTT connection refused: reason_code=5` | Kredensial MQTT salah | Cek `MQTT_USERNAME`/`MQTT_PASSWORD` |
| `TimeoutError` saat connect MQTT | Port/broker salah, atau TLS tidak aktif | Pastikan `MQTT_PORT=8883` dan broker host benar |
| Container restart-loop | Env var wajib kosong (`_require_env` gagal) | Cek log, pastikan 6 env var terisi |
| Data tidak masuk dashboard | Bridge tidak connect broker, atau supabase key salah | Cek log console, test dengan `mqtt_probe.py` lokal |
| Tidak ada command terkirim | Bridge tidak polling / RLS blok | Cek log `cmd-poll`, pastikan `SUPABASE_SERVICE_KEY` valid |

---

## 7. Matikan / hapus

```bash
# Hentikan sementara (replicas = 0)
az containerapp update --name rempah-bridge --resource-group rempah-rg \
  --min-replicas 0 --max-replicas 0

# Hapus total (hati-hati: hapus resource group = semua hilang)
az group delete --name rempah-rg --yes --no-wait
```

### Nonaktifkan sementara (pakai bridge lokal di laptop)

CLI menolak `--max-replicas 0`, jadi cara yang pasti untuk mematikan bridge
Azure adalah **deactivate revisi aktif** — replica langsung `NotRunning` dan
tidak perlu menunggu scale-down:

```bash
# 1. Cek nama revisi aktif
az containerapp revision list --name rempah-bridge --resource-group rempah-rg --query "[].name" -o tsv
# 2. Matikan revisi (replica berhenti)
az containerapp revision deactivate --name rempah-bridge --resource-group rempah-rg --revision <nama-revisi>
# 3. Verifikasi
az containerapp replica list --name rempah-bridge --resource-group rempah-rg
az containerapp replica show --name rempah-bridge --resource-group rempah-rg --replica <nama-replica> --query "properties.runningState"
```

Untuk menghidupkan kembali (kembali ke Azure):

```bash
az containerapp revision activate --name rempah-bridge --resource-group rempah-rg --revision <nama-revisi>
az containerapp update --name rempah-bridge --resource-group rempah-rg --min-replicas 1 --max-replicas 1
```

> ⚠️ Jangan jalankan bridge Azure dan bridge lokal bersamaan — dua bridge
> akan memproses command yang sama (terkirim 2× ke device) dan meng-insert
> telemetry dobel ke `sensor_logs`.

---

## Catatan biaya (estimasi)

- Container Apps: per-vCPU-RAM per detik. 1 vCPU / 1 GiB kira-kira **$70/bln**
  (running 24/7) — bisa lebih murah dengan `--min-replicas 0` saat tidak dipakai
  (tapi itu berarti bridge mati, data berhenti masuk).
- ACR Basic: **$5/bln** (0,1 GB storage gratis).
- Trial Azure $200 gratis biasanya cukup untuk lomba.

---

## Alternatif: Container Instances (lebih sederhana)

Kalau mau paling cepat (tidak perlu Container Apps environment):

```bash
az container create \
  --resource-group rempah-rg \
  --name rempah-bridge \
  --image rempahacr.azurecr.io/rempah-bridge:latest \
  --registry-login-server rempahacr.azurecr.io \
  --registry-username rempahacr \
  --registry-password "$(az acr credential show --name rempahacr --query 'passwords[0].value' -o tsv)" \
  --environment-variables \
    MQTT_BROKER="<broker-host>" \
    MQTT_PORT="8883" \
    MQTT_USERNAME="rempah-bridge" \
    MQTT_PASSWORD="<bridge-mqtt-password>" \
    SUPABASE_URL="<supabase-url>" \
    SUPABASE_SERVICE_KEY="<service-role-key>" \
  --restart-policy Always \
  --os-type Linux
```

Cek log: `az container logs --name rempah-bridge --resource-group rempah-rg`.

---

## Checklist singkat

- [ ] Install & login Azure CLI
- [ ] Buat resource group + ACR
- [ ] Build & push image bridge
- [ ] Buat Container Apps env + deploy (atau Container Instances)
- [ ] Set 6 env var wajib (MQTT + Supabase)
- [ ] Verifikasi log: `MQTT connected`
- [ ] Nyalakan device asli → cek data masuk ke Supabase
