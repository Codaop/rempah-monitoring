# 66 — Threshold bahaya suhu & massa gas disesuaikan

**What to build:** Status bahaya yang muncul di log sistem saat alat distilasi
mengikuti ambang baru:

- **Suhu boiler:** rentang 100–105 °C (dan di bawahnya, fase pemanasan) **tidak
  masuk danger**. DANGER hanya jika suhu **melebihi 105 °C**. Tier WARNING
  lama (`>92 °C`) dihapus — status cukup OK (≤105 °C) atau DANGER (>105 °C).
- **Massa gas:** DANGER jika massa gas **di bawah 4 kg**; **≥ 4 kg** dianggap
  normal/OK. (Kalibrasi load cell terakhir terbaca ±7 kg dan mendekati berat
  asli saat ditimbang manual — ambang 4 kg adalah batas isi gas tersisa.)

Perubahan berlaku konsisten di seluruh tempat yang menurunkan status dari
telemetry: baris status "Lonjakan Suhu Boiler" dan "Massa Gas" di log sistem &
PDF laporan (halaman analitik), dan alert suhu realtime di dashboard yang
selama ini memakai ambang lama.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Status suhu di log sistem (tabel & PDF analitik): OK untuk ≤105 °C, DANGER hanya untuk >105 °C — tidak ada lagi tier WARNING suhu
- [ ] Status massa gas di log sistem (tabel & PDF analitik): DANGER untuk <4 kg, OK untuk ≥4 kg
- [ ] Alert "suhu boiler tinggi" realtime di dashboard mengikuti ambang baru (>105 °C), bukan ambang lama
- [ ] Rentang 100–105 °C tidak memicu status danger di semua tempat di atas
- [ ] Verifikasi manual: suhu sintetis 100–105 °C → status OK; 106 °C+ → DANGER; massa gas 3,9 kg → DANGER; 4 kg+ → OK

**Catatan:** nilai ambang suhu dipakai juga oleh alert over-temperature di
bridge (`OVER_TEMP_THRESHOLD_C`, default 100 °C). Jika alert itu masih
dipakai, nilainya perlu disesuaikan ke 105 °C saat bridge di-deploy berikutnya
— di luar perubahan kode dashboard ini.
