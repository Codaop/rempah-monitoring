# 31 — Dashboard: status online/offline jujur dari `last_seen_at`

**What to build:** Status "Sensor Online/Offline" di dashboard tidak lagi dihitung dari kapan dashboard terakhir fetch data (`lastSync` — selalu hijau, bohong), melainkan dari `devices.last_seen_at` per perangkat dengan threshold offline 60 detik (sesuai `OFFLINE_AFTER_S` bridge). Pill "Terhubung" juga dibuat truthful — menunjukkan bahwa data benar-benar mengalir. Threshold dot di PowerPanel disamakan (saat ini 45s) menjadi 60s agar konsisten.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Perangkat yang diam >60s tampil "Offline" meski dashboard masih bisa polling
- [ ] Pill "Terhubung" mencerminkan kondisi nyata, bukan hardcoded
- [ ] Threshold offline konsisten antara dashboard (60s) dan PowerPanel
