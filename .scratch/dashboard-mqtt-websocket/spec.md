# Dashboard — Live Metrics via MQTT WebSocket

Status: ready-for-agent

## Problem Statement

Saat ini seluruh data live pada dashboard web (metric cards: Suhu Boiler, Massa Gas, Suhu Pendingin, plus sparkline) mengalir lewat rantai: ESP32 → broker MQTT (HiveMQ Cloud) → bridge Python → Supabase → Realtime → dashboard. Rantai ini membuat tampilan live bergantung pada kesehatan bridge (di mana pun ia di-deploy — laptop lokal maupun Azure): ketika bridge mati atau tertunda, metric cards ikut membeku padahal data sebenarnya masih mengalir di broker. Selain itu, jalur ini menambah latensi karena setiap nilai telemetry harus ditulis ke database dulu sebelum sampai ke browser.

Perubahan yang diinginkan: metric cards mengambil data **langsung dari broker MQTT lewat WebSocket (WSS)** — browser terhubung langsung ke HiveMQ Cloud — sementara **database tetap menjadi sumber kebenaran** untuk riwayat (`sensor_logs`), users/auth, lifecycle batch, perintah (`commands`), serta laporan PDF dan analitik.

## Solution

Dashboard (browser) membuka koneksi MQTT over WebSocket ke broker HiveMQ Cloud yang sama dengan yang dipakai ESP32, subscribe ke topik `rempah/+/telemetry` dan `rempah/+/state`, lalu menyaring pesan hanya untuk device milik operator. Aliran MQTT ini menjadi sumber utama untuk metric cards dan sparkline real-time. Riwayat tetap diambil dari Supabase untuk keperluan seed awal sparkline, analitik, dan laporan. Ketika koneksi WebSocket terputus, dashboard otomatis fallback ke jalur Supabase Realtime/polling yang sudah ada sehingga tidak ada regresi fungsional.

## User Stories

1. Sebagai operator, saya ingin metric card Suhu Boiler ter-update langsung dari broker MQTT tanpa perantara bridge lokal, sehingga nilai tetap segar walaupun bridge sedang mati.
2. Sebagai operator, saya ingin metric card Massa Gas ter-update langsung dari broker MQTT, sehingga saya bisa memantau konsumsi LPG secara real-time.
3. Sebagai operator, saya ingin metric card Suhu Pendingin ter-update langsung dari broker MQTT, sehingga pendinginan terpantau akurat.
4. Sebagai operator, saya ingin sparkline setiap metric ter-update dengan nilai telemetry terbaru dari MQTT, sehingga tren pergerakan tetap terlihat tanpa refresh manual.
5. Sebagai operator, saat pertama kali halaman dimuat, saya ingin sparkline ter-seed dari riwayat Supabase, sehingga grafik tidak mulai kosong ketika belum ada telemetry yang lewat di sesi browser.
6. Sebagai operator, saya ingin mode device (IDLE/PREHEAT/DISTILLING/...) tampil akurat dari pesan state MQTT yang retained, sehingga panel status tidak menunggu telemetry berikutnya.
7. Sebagai operator, ketika koneksi WebSocket terputus, saya ingin dashboard tetap menampilkan data live lewat jalur Supabase Realtime yang ada, sehingga saya tidak kehilangan pantauan.
8. Sebagai operator, saya ingin indikator status koneksi MQTT (terhubung/terputus) terlihat di dashboard, sehingga saya tahu jalur mana yang sedang aktif.
9. Sebagai operator, saya tidak ingin perubahan alur data ini mengubah cara saya mengirim perintah (mulai/mati), sehingga workflow operasional tetap sama.
10. Sebagai operator, saya ingin seluruh riwayat sensor tetap tersimpan di database, sehingga laporan PDF dan halaman analitik tidak berubah perilakunya.
11. Sebagai operator, saya ingin pesan telemetry dari device yang bukan milik saya tidak tampil, sehingga data antar producer tidak bocor di tampilan.
12. Sebagai admin, saya ingin kredensial MQTT dashboard memakai user yang sama dengan device, sehingga tidak perlu mengelola user tambahan di HiveMQ Cloud Console.
13. Sebagai developer, saya ingin konfigurasi koneksi MQTT dashboard berada di environment variable build (VITE_*), sehingga tiap environment bisa memakai broker berbeda.
14. Sebagai operator, ketika bridge mati, saya tetap bisa melihat nilai live, tetapi riwayat tetap berhenti tercatat — dan saya ingin hal ini jelas, sehingga saya tahu data yang tampil adalah data saat ini, bukan data terekam.

## Implementation Decisions

### Broker & kredensial
- **Cluster broker tetap sama** dengan yang dipakai ESP32 (HiveMQ Cloud Serverless, per ADR 0003). Tidak perlu membuat cluster baru.
- Kredensial dashboard memakai **user yang sama dengan device** (`rempah_hivemq` + password yang dipakai firmware sekarang) — keputusan user. Tidak perlu membuat user baru di HiveMQ Cloud Console.
- Konsekuensi: kredensial device kini ikut terekspos di bundle browser (public). Batasi pemakaiannya hanya untuk koneksi MQTT; bila nanti perlu rotasi, firmware dan dashboard harus di-update bersamaan.
- **Keterbatasan free tier**: HiveMQ Cloud Serverless tidak menyediakan ACL per-user/topic, sehingga siapa pun dengan kredensial itu bisa menerima semua topik. Untuk proyek single-producer (lomba) ini aman; mitigasi dilakukan client-side dengan menyaring hanya device milik operator (daftar device dari Supabase, ter-scope RLS). Dokumentasikan keterbatasan ini di UI/docs.

### Koneksi WebSocket
- URL: `wss://<broker-host>:8884/mqtt` — port 8884 (TLS) dan path `/mqtt` adalah standar HiveMQ Cloud untuk MQTT over WebSocket. **Perlu diverifikasi di console HiveMQ Cloud saat implementasi** (port bisa berbeda per cluster).
- Konfigurasi via environment variable build dashboard:
  - `VITE_MQTT_URL` → `wss://bde4a0fdcf30401db2125620c5950fa9.s1.eu.hivemq.cloud:8884/mqtt`
  - `VITE_MQTT_USERNAME` → `rempah_hivemq` (kredensial yang sama dengan device)
  - `VITE_MQTT_PASSWORD` → password `rempah_hivemq` yang dipakai firmware saat ini
- Subscribe: `rempah/+/telemetry` dan `rempah/+/state`. Pesan `state` bersifat retained sehingga mode device langsung tersedia saat subscribe, tidak menunggu 5 detik telemetry.
- Quality of Service: QoS 1 untuk telemetry (konsisten dengan firmware), non-retained.

### Modul baru `src/lib/mqtt.js`
- Wrapper tipis di atas library `mqtt.js` (dependensi baru di `dashboard/package.json`):
  - `connect()`, `disconnect()`, `subscribe(topics)`, `onMessage(callback)`.
  - Reconnect otomatis dengan backoff; status koneksi diekspos sebagai reactive state (connected / reconnecting / offline).
  - Ring buffer per device_id untuk sparkline (mis. 60 titik terakhir per metrik).
  - Parsing payload JSON telemetry `{ts, boiler_temp_c, cooling_temp_c, gas_mass_kg, water_level, drip_count, flame_lit}` dan state `{device_id, mode, cause, command_id?, ts}`.
- Pemetaan ke tampilan:
  - `boiler_temp_c` → card Suhu Boiler
  - `gas_mass_kg` → card Massa Gas
  - `cooling_temp_c` → card Suhu Pendingin
  - `mode` dari state → indikator mode device di panel

### Alur data di Dashboard.vue
- Saat mount: muat daftar device (Supabase, RLS), seed sparkline dari riwayat `sensor_logs`, lalu mulai koneksi MQTT.
- Selama terhubung: metric cards dan sparkline di-update dari aliran MQTT (per device terpilih).
- Saat terputus: fallback ke jalur yang sudah ada sekarang (Supabase Realtime channel `dashboard-live` / polling 30 detik) sehingga halaman tetap berfungsi. Indikator di UI memberi tahu jalur mana yang aktif.
- Perintah (mulai/mati/estop) **tidak berubah**: tetap insert ke tabel `commands`, diproses bridge. Di luar scope untuk dipindah ke WebSocket.

### Bridge & database
- **Bridge Python tidak diubah**. Tugasnya tetap: persistensi telemetry, validasi & forward command, lifecycle batch, kalkulasi yield/estimasi, alert, deteksi offline.
- Database tetap sumber kebenaran untuk riwayat, users, batch, dan laporan. Tidak ada skema baru yang wajib; perubahan skema hanya jika dibutuhkan (mis. menyimpan status koneksi jalur, opsional).

## Testing Decisions

- **Verifikasi manual/E2E** (keputusan user — tidak menambah framework test di dashboard):
  - Buka dashboard tanpa bridge lokal berjalan → metric cards tetap hidup dari MQTT WebSocket; sparkline bergerak.
  - Matikan broker/putuskan jaringan → dashboard fallback ke Supabase Realtime dan menampilkan indikator; tidak ada error fatal.
  - Mulai batch & kirim perintah → alur command via `commands` → bridge tetap bekerja seperti sebelumnya.
  - Buka halaman Analytics & unduh laporan PDF → data riwayat dari database utuh, tidak terpengaruh jalur live.
  - Verifikasi hanya device milik operator yang tampil saat ada lebih dari satu device di broker.
  - Ukur delay yang dirasakan antara tampilan dashboard dan nilai di Serial Monitor/firmware; sesuaikan bila perlu.
- **Good test = perilaku eksternal pada seam dashboard** (jalur MQTT vs jalur database): hasil yang diamati adalah nilai yang tampil di metric cards dan konsistensinya dengan riwayat.

## Out of Scope

- Mengubah bridge Python (persistensi, command, batch lifecycle, alert).
- Mengirim perintah lewat WebSocket MQTT — perintah tetap lewat `commands` → bridge.
- Menambahkan ACL/per-topic authorization di broker (tidak tersedia di free tier).
- Menghapus persistensi riwayat `sensor_logs` ke database.
- Perubahan pada halaman Analytics/Report selain yang menyangkut sumber data live.
- Dukungan multi-producer dengan pemisahan ketat (mitigasi hanya client-side filtering).

## Further Notes

1. Port WSS (8884) dan path `/mqtt` adalah standar HiveMQ Cloud, tetapi **wajib diverifikasi di console** saat implementasi karena bisa berbeda per cluster/region.
2. `mqtt.js` akan menjadi dependensi baru satu-satunya; ukuran bundle bertambah namun dapat di-code-split.
3. Kredensial device (`rempah_hivemq`) kini ikut terekspos di bundle browser karena dipakai juga oleh dashboard — rotasi berarti update firmware + dashboard bersamaan.
4. Sinkronisasi semantik offline: bridge menandai device offline setelah 60 detik tanpa telemetry (`OFFLINE_AFTER_S`, ticket 31). Indikator koneksi jalur MQTT di dashboard adalah status koneksi browser ↔ broker, bukan status device — dua hal berbeda dan tidak boleh dicampur di UI.
5. Sparkline ter-seed dari riwayat Supabase saat load awal agar grafik langsung penuh; sesudah itu aliran MQTT mengambil alih.
