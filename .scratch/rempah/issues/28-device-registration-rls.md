# 28 — Migration + RLS: operator boleh daftarkan device milik producer

**What to build:** Policy Row-Level Security pada tabel `devices` sehingga operator dapat membuat (INSERT) dan membaca (SELECT) device milik producer-nya sendiri — dibatasi `producer_id = operator_producer_id()` — tanpa membuka akses antar producer. Ini prasyarat agar registrasi perangkat dari web (ticket 36) bisa berfungsi.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Operator dapat INSERT baris `devices` dengan `producer_id` miliknya
- [ ] Operator tidak dapat membaca/membuat device producer lain (RLS tetap ketat)
- [ ] Bridge (service_role) tidak terpengaruh — tetap bypass RLS
