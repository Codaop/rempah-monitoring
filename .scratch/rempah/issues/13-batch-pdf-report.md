# 13 — Batch-scoped PDF report

**What to build:** The `/analytics` PDF report becomes batch-scoped: preview and download of a batch report containing batch identity, start/end, duration, Charge Mass, target vs estimated yield, peak temperature, and key events — generated client-side (print-to-PDF), no server round-trip.

**Blocked by:** 11, 12

**Status:** ready-for-agent

- [ ] Preview renders from batch data for a chosen batch.
- [ ] Download produces a PDF without a server component.
- [ ] Works on static hosting exactly like the rest of the dashboard.