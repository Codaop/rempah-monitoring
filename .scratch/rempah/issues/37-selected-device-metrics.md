# 37 — Dashboard: state perangkat terpilih + metrik per device

**What to build:** State perangkat terpilih diangkat dari `PowerPanel` (saat ini `selectedIdx` internal) ke `Dashboard.vue` melalui v-model, sehingga kartu metrik, sparkline, dan filter realtime memakai device terpilih — bukan device pertama. Dengan beberapa perangkat asli, setiap still menampilkan datanya sendiri secara akurat tanpa tercampur.

**Blocked by:** 35 — Dashboard kartu metrik hidup saat IDLE

**Status:** ready-for-agent

- [ ] Memilih device lain di PowerPanel mengubah metrik & sparkline yang ditampilkan
- [ ] Realtime hanya memperbarui data device yang sedang terpilih
- [ ] State pilihan bertahan saat polling/refresh data
