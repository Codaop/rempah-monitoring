# 63 — UI: tombol hapus di daftar device + modal konfirmasi

**What to build:** Tombol "Hapus" pada setiap baris device di halaman Settings (DeviceManager) yang memungkinkan operator menghapus device dari dashboard dengan satu klik konfirmasi. Setelah berhasil, device hilang dari semua tampilan (Settings dan Dashboard) tanpa reload penuh.

**Blocked by:** 62 — Fondasi DB: fungsi RPC `delete_device`

**Status:** ready-for-agent

- [ ] Setiap baris device di `DeviceManager.vue` menampilkan tombol **Hapus** berwarna merah/abu (sekadar aksi destruktif).
- [ ] Klik "Hapus" membuka **AppModal** yang menampilkan nama device, peringatan bahwa seluruh riwayat batch/laporan akan terhapus permanen, dan status batch aktif (jika ada) yang menjadi alasan pemblokiran.
- [ ] Tombol "Ya, Hapus" dalam modal otomatis nonaktif jika device memiliki batch aktif; label modal menyesuaikan ("Hapus Device X?" atau "Tidak bisa dihapus karena masih ada batch aktif").
- [ ] Konfirmasi sukses → panggil RPC `delete_device(device_id)` dari Supabase client → refresh daftar device lokal tanpa reload halaman (`loadDevices()`). Tampilkan notifikasi sukses singkat ("Perangkat XXX berhasil dihapus.").
- [ ] Gagal / error RLS/gagal koneksi → tampilkan pesan error di UI tanpa memadamkan modal.
- [ ] Perangkat yang sudah dihapus tidak muncul lagi di dashboard setelah refresh normal (10 detik auto-refresh, tombol manual, atau navigasi ulang).
