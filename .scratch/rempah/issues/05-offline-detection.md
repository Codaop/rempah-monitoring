# 05 — Offline detection

Status: ready-for-agent

## Problem

Operators need to know when a device is unreachable so they don't fire commands into the void.

## Requirements

- Bridge derives `last_seen_at` on `devices` from the telemetry/state cadence.
- Device flagged offline after 1 minute of silence (~12 missed 5s ticks).
- Offline flag surfaces through the dashboard data path (device state or separate field).

Blocked by: 01, 02