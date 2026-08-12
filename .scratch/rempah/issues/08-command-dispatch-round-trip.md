# 08 — Command dispatch round-trip (dashboard → bridge → device)

**What to build:** The first half of the command loop closes: an operator's button press inserts a `commands` row; the Bridge (subscribed to new commands via Realtime, falling back to polling) validates `expected_state` against `device_state` and either forwards the command to `rempah/{device_id}/command` tagged with `command_id`, or marks it `rejected`. A stale-state press is rejected and the dashboard shows the refresh prompt instead of an action on outdated beliefs.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Valid command is forwarded on the device command topic with `command_id`.
- [ ] State mismatch → `commands.status = rejected`, nothing forwarded.
- [ ] Emergency stop is always forwarded regardless of state.
- [ ] Dashboard refresh prompt appears on rejection.