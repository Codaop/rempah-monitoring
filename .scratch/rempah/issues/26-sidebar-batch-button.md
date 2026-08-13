# 26 — Tombol sidebar "Mulai Batch Baru": muncul saat batch aktif

**What to build:** Tombol "Mulai Batch Baru" di navigasi samping hanya muncul ketika sudah ada batch yang sedang berjalan — tujuannya agar operator dapat menyiapkan batch berikutnya selama batch sekarang disuling. Tombol menjadi abu-abu/tidak bisa diklik ketika tidak ada perangkat yang tersedia, dan mengkliknya langsung membuka modal form batch baru (alur yang sama dengan panel batch).

**Blocked by:** 24

**Status:** done

- [x] Saat tidak ada batch aktif, tombol tidak muncul di navigasi samping
- [x] Saat ada batch aktif, tombol muncul; mengkliknya membuka modal form batch baru (alur sama dengan ticket 24)
- [x] Saat tidak ada perangkat tersedia untuk batch baru, tombol tampil abu-abu/tidak bisa diklik
- [x] Perilaku konsisten di semua halaman (dashboard, analitik & log, profil); di layar kecil tombol tetap mengikuti desain navigasi yang ada

## Comments

- 2026-08-13: AppShell.vue kini memuat status batch aktif + daftar perangkat (dengan mode dari device_state) setiap mount + poll 30 dtk. Tombol `.side-foot` hanya dirender saat `hasActiveBatch`, disabled saat `anyDeviceAvailable` false, dan kliknya navigasi ke dashboard dengan `?start=` yang membuka modal form (ticket 24). Di layar kecil tombol tetap tersembunyi sesuai desain top-nav. Diverifikasi via `npm run build`.
