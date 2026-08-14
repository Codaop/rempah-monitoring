# 32 — Dashboard: feedback status eksekusi command

**What to build:** Dashboard saat ini hanya mendengarkan INSERT pada tabel `commands`, sehingga operator tidak pernah melihat hasil akhir perintah (dispatched / succeeded / failed / rejected). Tambahkan subscribe UPDATE `commands` dan tampilkan perubahan status tersebut di NotificationLog serta catatan di PowerPanel, sehingga operator tahu perintahnya benar-benar dieksekusi atau ditolak (user story 21–22).

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Perubahan status command (succeeded/failed/rejected/dispatched) muncul di notifikasi
- [ ] Label status ditampilkan dalam Bahasa Indonesia yang jelas (Sukses/Ditolak/Gagal)
- [ ] Tidak ada duplikasi notifikasi saat status berubah beberapa kali
