# 29 — Nav: ganti "Profil" → "Pengaturan" + grouping sidebar

**What to build:** Sidebar (`AppShell.vue`) dirombak: item "Profil" diganti "Pengaturan" dengan ikon gear, dan menu dikelompokkan dengan label section — `UTAMA` (Dasbor, Analitik & Log) dan `PENGATURAN` (Pengaturan) — sebagai pemisah visual antar kelompok. Ini prefactor untuk halaman Pengaturan (ticket 34) dan manajemen perangkat.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Item menu "Pengaturan" berikon gear tampil menggantikan "Profil"
- [ ] Ada pemisah/group label antara menu utama dan menu pengaturan di sidebar
- [ ] Navigasi & active state tetap berfungsi di semua ukuran layar (responsif)
