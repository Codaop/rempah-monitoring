# 13 — Batch-scoped PDF report

**What to build:** The `/analytics` PDF report becomes batch-scoped: preview and download of a batch report containing batch identity, start/end, duration, Charge Mass, target vs estimated yield, peak temperature, and key events — generated client-side (print-to-PDF), no server round-trip.

**Blocked by:** 11, 12

**Status:** done

- [x] Preview renders from batch data for a chosen batch.
- [x] Download produces a PDF without a server component.
- [x] Works on static hosting exactly like the rest of the dashboard.

## Comments

- 2026-08-12: Implemented in `Analytics.vue`. Batch picker (20 batch terbaru, RLS-scoped) + ringkasan pada kartu laporan; `openReport` merender HTML batch-scoped (identitas batch, perangkat, mulai/selesai, durasi, Massa Muatan, suhu puncak, hasil estimasi vs target + %, hasil akhir, kejadian penting dari `commands`/`alerts` dalam jendela batch) lalu print-to-PDF client-side — tanpa server.
- 2026-08-12: `npm run build` succeeds.