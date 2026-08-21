from typing import Callable, Protocol

from rempah_bridge.model import Command, DeviceState
from rempah_bridge.ports import DbPort, MqttPort

import time
from datetime import datetime, timezone


# Both action names are accepted so the dashboard's "EMERGENCY_STOP" and the
# firmware contract's "ESTOP" both bypass state validation.
_ESTOP_ACTIONS = {"ESTOP", "EMERGENCY_STOP"}

# Modes that count as "heating" (open a pending batch) and "run over" (close).
_HEATING_MODES = {"PREHEAT", "DISTILLING"}
_TERMINAL_MODES = {"IDLE", "ERROR", "ESTOP"}


class Bridge:
    def __init__(
        self,
        mqtt: MqttPort,
        db: DbPort,
        over_temp_threshold_c: float = 100.0,
        offline_after_s: float = 60.0,
        clock: Callable[[], float] = time.time,
        drip_ml: float = 0.05,
        topic_root: str = "rempah",
    ) -> None:
        self.mqtt = mqtt
        self.db = db
        self.over_temp_threshold_c = over_temp_threshold_c
        self.offline_after_s = offline_after_s
        self.clock = clock
        self.drip_ml = drip_ml
        self.topic_root = topic_root
        self._drips: dict[str, int] = {}

    @staticmethod
    def _coerce_ts(value: object, fallback_epoch: float) -> str:
        """Kembalikan `ts` payload yang valid ISO 8601; fallback ke waktu terima
        bridge bila tidak valid (angka, string non-tanggal, atau format waktu
        saja). Device yang salah format tidak boleh mematikan pipeline
        telemetry — lebih baik timestamp terima bridge daripada data hilang
        (pola yang sama dengan first_seen_at, ticket 41).
        """
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if isinstance(parsed, datetime):  # bukan objek time ("10:00:00")
                    return value
            except ValueError:
                pass
        return datetime.fromtimestamp(fallback_epoch, tz=timezone.utc).isoformat()

    def process_command(self, command: Command) -> None:
        if command.action in _ESTOP_ACTIONS:
            self._forward(command)
            return
        current = self.db.device_state(command.device_id)
        if current.mode == command.expected_state:
            self._forward(command)
        else:
            self.db.mark_command(command.id, "rejected")

    def _forward(self, command: Command) -> None:
        self.mqtt.publish(
            f"{self.topic_root}/{command.device_id}/command",
            {"command_id": command.id, "action": command.action},
        )
        self.db.mark_command(command.id, "dispatched")

    def handle_telemetry(self, device_id: str, payload: dict) -> None:
        # Ticket 43: pesan dari device yang tidak terdaftar dicatat (bukan drop
        # diam-diam) — kesalahan konfigurasi firmware cepat ketahuan.
        if not self.db.is_known_device(device_id):
            self.db.record_unknown_message(
                device_id, f"{self.topic_root}/{device_id}/telemetry", payload
            )
            return
        # Timestamp first contact memakai waktu terima bridge, bukan `ts` dari
        # payload — retained state lama bisa membawa `ts` usang dan membuat
        # first_seen_at mencatat waktu yang salah (ticket 41).
        now = self.clock()
        # `ts` payload yang rusak (mis. "955848") diganti waktu terima bridge
        # supaya insert sensor_logs tidak ditolak Postgres (ticket 49).
        payload = {**payload, "ts": self._coerce_ts(payload.get("ts"), now)}
        self.db.insert_telemetry(device_id, payload)
        self.db.set_last_seen(device_id, now)
        self.db.set_offline(device_id, False)
        self.db.note_first_contact(device_id, now)
        temp = payload.get("boiler_temp_c")
        if temp is not None and temp > self.over_temp_threshold_c:
            self.db.insert_alert(device_id, "over_temperature", temp, payload["ts"])
        drips = payload.get("drip_count", 0)
        if drips:
            self._drips[device_id] = self._drips.get(device_id, 0) + drips
            estimated_yield_l = self._drips[device_id] * self.drip_ml / 1000
            self.db.update_estimate(device_id, estimated_yield_l, payload["ts"])

    def handle_state(self, payload: dict) -> None:
        device_id = payload["device_id"]
        # Ticket 43: device tak dikenal dicatat, state-nya tidak diterapkan.
        if not self.db.is_known_device(device_id):
            self.db.record_unknown_message(
                device_id, f"{self.topic_root}/{device_id}/state", payload
            )
            return
        mode = payload["mode"]
        ts = self._coerce_ts(payload.get("ts"), self.clock())
        previous = self.db.device_state(device_id)  # read before overwriting
        self.db.set_device_state(device_id, mode, ts)
        self.db.note_first_contact(device_id, self.clock())
        cause = payload.get("cause", "")
        if cause.startswith("command_executed:"):
            self.db.mark_command(cause.split(":", 1)[1], "succeeded")
        elif cause.startswith("command_failed:"):
            self.db.mark_command(cause.split(":", 1)[1], "failed")
        # Batch lifecycle: a pending batch opens when heating starts and the
        # active batch closes when the run ends (per ADR 0002, boundaries come
        # from device-state transitions, not manual bookkeeping).
        if mode in _HEATING_MODES and previous.mode not in _HEATING_MODES:
            self.db.open_pending_batch(device_id, ts)
        elif mode in _TERMINAL_MODES and previous.mode not in _TERMINAL_MODES:
            self.db.close_active_batch(device_id, ts)

    def check_offline(self) -> None:
        now = self.clock()
        for device_id in self.db.list_devices():
            last_seen = self.db.get_last_seen(device_id)
            if last_seen is not None and now - last_seen > self.offline_after_s:
                self.db.set_offline(device_id, True)
