# 22 — Toggle daya: gestur tarik + konfirmasi aksi irreversible

**What to build:** Tombol daya di panel kontrol menjadi interaksi yang benar-benar bisa ditarik sesuai label "Tarik untuk nyalakan/mematikan": operator menggeser lingkaran toggle ke sisi ON/OFF, dan setiap aksi yang menghentikan proses (mematikan daya saat distilasi berjalan, emergency stop) dikonfirmasi dulu lewat modal agar tidak terjadi pemadaman tak sengaja.

**Blocked by:** 20

**Status:** done

- [x] Lingkaran toggle dapat digeser dengan drag (mouse & sentuh, via pointer events) ke arah ON/OFF; melepas di sisi yang benar mengirim perintah daya
- [x] Tetap bisa dioperasikan via klik dan keyboard (tab + enter/spasi) sebagai fallback aksesibilitas
- [x] Umpan balik visual jelas: posisi lingkaran mengikuti drag, warna track/circle berubah, dan kontrol nonaktif (disabled) saat perintah sedang dikirim
- [x] Mematikan daya saat batch sedang berjalan memunculkan modal konfirmasi; hanya setelah dikonfirmasi perintah POWER_OFF dikirim
- [x] Emergency Stop memunculkan modal konfirmasi bergaya bahaya; hanya setelah dikonfirmasi perintah EMERGENCY_STOP dikirim
- [x] Membatalkan/ESC menutup modal tanpa mengirim apa pun
- [x] Komponen modal reusable (ticket 20) dipakai di sini; build dashboard lulus

## Comments

- 2026-08-13: PowerPanel.vue ditulis ulang: drag pointer-events (pointer capture, threshold setengah track), snap posisi ON kanan / OFF kiri, tap tanpa geser tetap jadi toggle klik, keyboard Enter/Space fallback. Prop `batchActive` baru dari Dashboard. Konfirmasi POWER_OFF hanya saat batch aktif; EMERGENCY_STOP selalu konfirmasi (modal AppModal). Diverifikasi via `npm run build`.
