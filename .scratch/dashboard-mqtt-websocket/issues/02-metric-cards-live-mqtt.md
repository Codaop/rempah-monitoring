# 02 — Metric cards & sparkline real-time dari MQTT

**What to build:** Tiga metric card (Suhu Boiler, Massa Gas, Suhu Pendingin)
beserta sparkline-nya di-update langsung dari aliran MQTT untuk device yang
sedang dipilih — tetap hidup walau bridge mati. Saat halaman pertama dimuat,
sparkline di-seed dari riwayat Supabase lalu disambung aliran live. Mode device
ikut ter-update dari pesan state yang retained.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Saat MQTT connected dan data segar, nilai card & sparkline bergerak
      real-time dari broker tanpa bergantung bridge.
- [ ] Saat berpindah device, tampilan langsung mengikuti device terpilih.
- [ ] Reload halaman → sparkline langsung terisi riwayat Supabase, lalu
      dilanjutkan data live MQTT.
- [ ] Mode device (IDLE / PREHEAT / DISTILLING / …) ter-update dari pesan
      state MQTT.
