# 65 — Metric card menampilkan 0 saat data broker berhenti bergerak

**What to build:** Empat metric card di dashboard utama (SUHU BOILER, MASSA
GAS, SUHU PENDINGIN, TOTAL TETESAN) menampilkan **0** (nol) ketika tidak ada
data segar yang datang dari broker HiveMQ untuk perangkat terpilih — yaitu saat
koneksi MQTT terputus **atau** telemetry terakhir sudah lebih dari 60 detik
(ambang offline device yang sudah ada). Saat data mengalir normal, card
menampilkan nilai live seperti sekarang; saat data berhenti, card tidak lagi
menampilkan nilai riwayat database yang basi (fallback DB dihapus), sparkline
menjadi kosong/datar, dan card otomatis kembali ke nilai live begitu data masuk
lagi — tanpa reload manual.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Card SUHU BOILER, MASSA GAS, SUHU PENDINGIN menampilkan 0 saat data live basi (telemetry terakhir > 60 detik) atau MQTT tidak terhubung
- [ ] Card TOTAL TETESAN menampilkan 0 saat data live basi — nilai tampilan tidak lagi memakai fallback riwayat DB (dripDbTotal/seedDrips)
- [ ] Sparkline keempat card kosong/datar saat data tidak segar (tidak memakai riwayat DB sebagai sumber gambar)
- [ ] Saat data segar kembali, card otomatis menampilkan nilai live tanpa reload manual
- [ ] Indikator status (dataFlowing, mqttLabel, label "Terhubung / Menunggu Data") tetap memakai logika timestamp — tidak terganggu oleh nilai card 0
- [ ] Verifikasi manual: matikan aliran data device → card berubah menjadi 0 dalam ≤60 detik; nyalakan kembali → card kembali ke nilai live
