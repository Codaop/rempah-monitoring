# Standar Proyek Rempah Monitoring

## Informasi Deploy

- **Project Name**: `rempah-monitoring`
- **Git Repository**: `https://github.com/Codaop/rempah-monitoring.git`
- **Vercel Project ID**: `prj_nhRVJr3e1xsWF2yEXLNRkQPXiUgo`
- **Vercel Team/Org**: `codaops-projects`
- **Production URL**: `https://rempah-monitoring.vercel.app`

## Struktur Direktori

```
rempah-monitoring/
├── dashboard/          # Frontend Vue.js dashboard
│   ├── src/views/
│   │   ├── Dashboard.vue    # Dashboard utama (kontrol perangkat)
│   │   └── Analytics.vue    # Halaman analitik & log
│   ├── src/components/        # Komponen Vue.js
│   ├── src/lib/               # Library (mqtt.js, supabase.js, dll)
│   └── src/views/             # Halaman-halaman aplikasi
├── .vercel/
│   └── project.json           # Konfigurasi proyek Vercel
├── vercel.json                # Config rewrite Vercel
└── package.json               # Dependensi Node.js
```

## Cara Deploy

### Deploy ke Production

```bash
# Dari root directory rempah-monitoring (bukan dashboard/)
cd rempah-monitoring
vercel --prod --scope=codaops-projects
```

### Build & Preview

```bash
# Build frontend
cd dashboard
npm run build
```

### Checklist Sebelum Deploy

- [ ] Jalankan `npm run build` dan pastikan tidak ada error
- [ ] Pastikan semua perubahan sudah `git add` dan `git commit`
- [ ] Push ke `origin/dev` terlebih dahulu
- [ ] Deploy dengan `vercel --prod --scope=codaops-projects`
- [ ] Verifikasi deployment di `https://rempah-monitoring.vercel.app`

## Fitur Dashboard Utama

### MQTT Connection Status
- `lastMessageAt`: tracking timestamp terakhir pesan MQTT dari broker
- `isReconnecting`: menampilkan "MQTT Menghubungkan…" saat >10 detik tidak ada data
- `mqttStatus`: idle | connecting | connected | reconnecting | offline
- `OFFLINE_MS = 60000` (1 menit): device dihitung mati jika tidak kirim data

### Resume Batch Terputus (Ticket 60)
- `interruptedBatch`: batch interrupted terbaru dari database
- `showResumeModal`: modal muncul saat device kembali online
- `resumeDeviceOnline`: menggunakan `lastMessageAt` (prioritas) atau `last_seen_at` (fallback)
- `resumeInterruptedBatch`: kirim RESUME_BATCH + POWER_ON command
- `startNewBatchInstead`: biarkan batch lama interrupted, buka form batch baru

### Device Dead Detection
- `sensorOnline`: menggunakan `offlineSince(d.last_seen_at) < OFFLINE_MS`
- Alert muncul saat device mati >1 menit tidak kirim data

### Tombol Batch Disable
- `hasOnlineDevice`: computed yang cek apakah ada device online
- Tombol "Lanjutkan Batch" dan "Mulai Batch Baru" disable saat tidak ada device online

### Header Badges
- Dashboard.vue: menampilkan sensor online/offline, MQTT status, data flowing
- Analytics.vue: header bersih tanpa status badges (hanya di Dashboard.vue)

## Standar Coding

- Gunakan `OFFLINE_MS = 60000` secara konsisten di seluruh project
- `REFRESH_MS = 10000` untuk auto-refresh data metric cards
- Gunakan `lastMessageAt` sebagai primary indicator koneksi broker MQTT
- Fallback ke `last_seen_at` dari database jika `lastMessageAt` tidak tersedia
