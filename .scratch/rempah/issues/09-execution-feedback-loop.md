# 09 — Execution feedback loop (device state closes the loop)

**What to build:** Device state messages close the loop on every command. When the device publishes a retained state after receiving a command, the Bridge updates `device_state.mode` and `commands.status` to `succeeded`/`failed`; the dashboard reflects the new mode and shows confirmation or a failure marker. Self-detected transitions (flame-out → ERROR, low water → ERROR, end-point reached) flow through the same path.

Contract (from the spec, the firmware must implement this): retained state on `rempah/{device_id}/state`, payload `{device_id, mode, cause, command_id?, ts}`; `cause` is `command_executed:<command_id>`, `command_failed:<command_id>`, or `detected`; modes are `IDLE / PREHEAT / DISTILLING / DRAINING / ERROR / ESTOP`.

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] `command_executed` → `device_state.mode` updated and `commands.status = succeeded`.
- [ ] `command_failed` → `commands.status = failed`; dashboard shows a clear failure marker.
- [ ] `detected` transitions update state with no associated command.
- [ ] Dashboard mode card and notification log reflect executed actions without manual refresh.