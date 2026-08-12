# 08 — PDF report export (client-side)

Status: ready-for-agent

## Problem

Operators need to preview and download a batch report as PDF (UI: "Pratinjau PDF" / "Unduh PDF").

## Requirements

- Client-side generation from batch data (batch logs, sensor_logs summary, estimated yield) — the lighter path chosen for v1.
- Preview panel on `/analytics` (blurred thumbnail) + download button.
- Content: batch identity, start/end, duration, Charge Mass, target vs estimated yield, peak temperature, key events.

## Acceptance

- Preview renders from batch data; download produces a PDF without a server round-trip.
- Works where the dashboard works (static hosting, no server component).

Blocked by: 06