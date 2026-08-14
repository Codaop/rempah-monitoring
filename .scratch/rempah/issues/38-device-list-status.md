# 38 — Daftar perangkat & status provisioning

**What to build:** Di section "Manajemen Perangkat": daftar semua device milik producer — nama, UUID, `mqtt_username`, status online (dari `last_seen_at`), dan topic MQTT-nya — lengkap dengan tombol untuk melihat kembali kartu flash provisioning per device (UUID, topic, kredensial). Operator dapat memantau perangkat mana yang sudah siap dipakai dan mana yang belum ter-provision.

**Blocked by:** 36 — Form registrasi device + kartu flash

**Status:** ready-for-agent

- [ ] Daftar menampilkan nama, UUID, mqtt_username, status online, dan topic tiap device
- [ ] Tombol "lihat kartu flash" membuka kembali detail provisioning device terkait
- [ ] Daftar ter-scope ke producer operator (multi-tenant aman)
