# 67 — Update 3 laporan batch_logs terbaru dengan data Uji 1, 2, 3

**What to build:** Meng-update `batch_logs` untuk 3 batch paling terakhir dengan data uji distilasi kapulaga. Data mencakup volume minyak, rendemen, konsumsi gas, durasi, suhu puncak, dan yield cair.

**Blocked by:** None — dapat langsung dijalankan

**Status:** ready-for-agent

- [ ] batch_logs `ec1a00e0` (Uji 1) di-update: oil_volume_ml=4, yield_rendemen_pct=0.8, gas_used_kg=0.096, duration=PT2H, peak_temp=101.97, yield_l=0.004
- [ ] batch_logs `d1c25f7b` (Uji 2) di-update: oil_volume_ml=12, yield_rendemen_pct=2.4, gas_used_kg=1.31, duration=PT3H45M, peak_temp=101.87, yield_l=0.012
- [ ] batch_logs `54de7cd5` (Uji 3) di-update: oil_volume_ml=16, yield_rendemen_pct=3.2, gas_used_kg=1.40, duration=PT4H, peak_temp=101.90, yield_l=0.016
- [ ] Verifikasi query SELECT menunjukkan data sudah benar setelah update
