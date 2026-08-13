# 24 — "Mulai Batch Baru" di panel batch: modal form pilih perangkat

**What to build:** Flow menambah batch distilasi baru dipindah ke panel progres batch: tombol "Mulai Batch Baru" tampil di tengah panel dan membuka modal form saat diklik. Operator **wajib memilih perangkat** yang akan dipakai, dan melihat status ketersediaan tiap perangkat (online + idle = tersedia) langsung di dalam modal. Saat tidak ada satu pun perangkat tersedia, tombol "Mulai Batch Baru" berubah abu-abu/tidak bisa diklik. Setelah submit, batch pending dibuat dan perintah pemanasan (POWER_ON) terkirim ke perangkat terpilih. Komponen lama untuk memulai batch (termasuk modal pemilihan sesi/perangkat) dihapus.

**Blocked by:** 20

**Status:** done

- [x] Komponen lama untuk memulai batch dihapus dan tidak dipakai lagi di halaman utama
- [x] Tombol "Mulai Batch Baru" tampil di tengah panel progres batch dan membuka modal form saat diklik
- [x] Modal menampilkan daftar perangkat lengkap dengan status ketersediaan (tersedia / tidak tersedia) berdasarkan kondisi online dan mode perangkat
- [x] Jika semua perangkat tidak tersedia, tombol "Mulai Batch Baru" nonaktif (abu-abu) dan tidak membuka modal
- [x] Form mengharuskan pemilihan perangkat (dari yang tersedia) dan massa muatan; target hasil opsional; validasi sebelum submit
- [x] Jika belum ada sesi terbuka, sesi dibuat otomatis dengan perangkat terpilih; jika sudah ada, batch masuk ke sesi aktif
- [x] Submit membuat batch pending dan mengirim perintah pemanasan (POWER_ON) ke perangkat terpilih; log/notifikasi muncul di dashboard
- [x] Pintasan dari halaman lain (mis. parameter start di URL) membuka modal form yang sama
- [x] Komponen modal reusable (ticket 20) dipakai di sini; build dashboard lulus

## Comments

- 2026-08-13: BatchStarter.vue DIHAPUS. BatchPanel.vue ditulis ulang: tombol "Mulai Batch Baru" di tengah (atas garis pemisah), disabled saat tidak ada perangkat tersedia (online <45 dtk + mode IDLE); modal AppModal berisi radio pilihan perangkat dengan badge status (Tersedia/mode/Offline), input massa muatan (wajib) + target hasil (opsional). Submit: buat sesi bila belum ada → insert batch pending → insert perintah POWER_ON → emit log + event `created` (Dashboard reload). Pintasan `?start=` di Dashboard kini memanggil `batchPanel.openModal()`. Diverifikasi via `npm run build`.
