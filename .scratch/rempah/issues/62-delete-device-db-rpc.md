# 62 — Fondasi DB: fungsi RPC `delete_device`

**What to build:** Satu fungsi server-side yang menghapus sebuah device beserta semua data turunannya secara transaksional dari database, sehingga operator bisa "membatalkan" pendaftaran device atau membersihkan perangkat lama tanpa akses developer ke database.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Fungsi SQL dibuat dan diterapkan sebagai migration di Supabase (`scripts/migrations/`).
- [ ] Fungsi menerima `device_id uuid` sebagai satu-satu parameter.
- [ ] **Guard aktif**: menolak jika device memiliki batch dengan status `active`. Return error terstruktur yang bisa ditampilkan di dashboard.
- [ ] Penghapusan berjalan dalam satu transaksi. Urutan penghapusan (yang punya FK → devices): `device_state`, `session_devices`, `commands`, `alerts`, `sensor_logs`, `batch_logs` (via batches), `batches`, lalu `devices` itu sendiri.
- [ ] Hanya owner producer yang bisa memanggil: fungsi mengecek `devices.producer_id = current_producer_id()` sebelum memulai penghapusan; menolak jika tidak cocok.
- [ ] Hasil return berupa JSON ringkasan jumlah baris per tabel yang dihapus.
- [ ] Test fungsi lewat SQL console / test migration: berhasil pada device tanpa data, device dengan riwayat penuh, refusal saat batch aktif, refusal lintas producer, dan rollback otomatis jika terjadi error di tengah aliran.
