from typing import Callable, List, Tuple

import pytest

from rempah_bridge.bridge import Bridge
from rempah_bridge.model import Command, DeviceState


class FakeMqtt:
    def __init__(self) -> None:
        self.published: List[Tuple[str, dict]] = []

    def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


class FakeDb:
    def __init__(self, state: DeviceState, last_seen: dict | None = None) -> None:
        self.state = state
        self.last_seen: dict[str, float] = last_seen or {}
        self.offline_flags: List[Tuple[str, bool]] = []
        self.status_updates: List[Tuple[str, str]] = []
        self.telemetry: List[dict] = []
        self.state_updates: List[dict] = []
        self.alerts: List[dict] = []
        self.estimates: List[dict] = []

    def device_state(self, device_id: str) -> DeviceState:
        return self.state

    def mark_command(self, command_id: str, status: str) -> None:
        self.status_updates.append((command_id, status))

    def insert_telemetry(self, device_id: str, payload: dict) -> None:
        self.telemetry.append({"device_id": device_id, **payload})

    def set_device_state(self, device_id: str, mode: str, ts: str) -> None:
        self.state_updates.append({"device_id": device_id, "mode": mode, "ts": ts})
        self.state = DeviceState(device_id=device_id, mode=mode)

    def insert_alert(self, device_id: str, kind: str, value: float, ts: str) -> None:
        self.alerts.append({"device_id": device_id, "kind": kind, "value": value, "ts": ts})

    def set_last_seen(self, device_id: str, ts: float) -> None:
        self.last_seen[device_id] = ts

    def get_last_seen(self, device_id: str) -> float:
        return self.last_seen.get(device_id)

    def list_devices(self) -> List[str]:
        return list(self.last_seen.keys())

    def set_offline(self, device_id: str, offline: bool) -> None:
        self.offline_flags.append((device_id, offline))

    def update_estimate(self, device_id: str, estimated_yield_l: float, ts: str) -> None:
        self.estimates.append(
            {"device_id": device_id, "estimated_yield_l": estimated_yield_l, "ts": ts}
        )


@pytest.fixture
def mqtt() -> FakeMqtt:
    return FakeMqtt()


def test_command_with_matching_expected_state_is_forwarded_on_command_topic(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c1", device_id="d1", action="STOP", expected_state="DISTILLING")

    bridge.process_command(command)

    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c1", "action": "STOP"})
    ]


def test_command_with_stale_expected_state_is_rejected_and_not_forwarded(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DRAINING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c1", device_id="d1", action="REFILL", expected_state="DISTILLING")

    bridge.process_command(command)

    assert mqtt.published == []
    assert db.status_updates == [("c1", "rejected")]


def test_emergency_stop_bypasses_validation_and_is_always_forwarded(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    estop = Command(id="c9", device_id="d1", action="ESTOP")

    bridge.process_command(estop)

    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c9", "action": "ESTOP"})
    ]


def test_telemetry_message_is_persisted(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "ts": "2026-08-11T10:00:00Z",
        "boiler_temp_c": 102.4,
        "gas_pressure_kpa": 2.8,
        "water_level": "OK",
        "drip_count": 3,
        "flame_lit": True,
    }

    bridge.handle_telemetry("d1", payload)

    assert db.telemetry == [{"device_id": "d1", **payload}]


def test_state_message_updates_device_state(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "DRAINING",
        "cause": "command_executed:c1",
        "ts": "2026-08-11T10:05:00Z",
    }

    bridge.handle_state(payload)

    assert db.state_updates == [
        {"device_id": "d1", "mode": "DRAINING", "ts": "2026-08-11T10:05:00Z"}
    ]


def test_command_executed_cause_marks_command_succeeded(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "DRAINING",
        "cause": "command_executed:c1",
        "ts": "2026-08-11T10:05:00Z",
    }

    bridge.handle_state(payload)

    assert db.status_updates == [("c1", "succeeded")]


def test_command_failed_cause_marks_command_failed(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "DISTILLING",
        "cause": "command_failed:c2",
        "ts": "2026-08-11T10:06:00Z",
    }

    bridge.handle_state(payload)

    assert db.status_updates == [("c2", "failed")]


def test_telemetry_above_threshold_raises_over_temperature_alert(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db, over_temp_threshold_c=100.0)
    payload = {
        "ts": "2026-08-11T10:10:00Z",
        "boiler_temp_c": 102.4,
        "gas_pressure_kpa": 2.8,
        "water_level": "OK",
        "drip_count": 3,
        "flame_lit": True,
    }

    bridge.handle_telemetry("d1", payload)

    assert db.alerts == [
        {"device_id": "d1", "kind": "over_temperature", "value": 102.4, "ts": "2026-08-11T10:10:00Z"}
    ]


def test_telemetry_below_threshold_raises_no_alert(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db, over_temp_threshold_c=100.0)
    payload = {
        "ts": "2026-08-11T10:11:00Z",
        "boiler_temp_c": 98.0,
        "gas_pressure_kpa": 2.8,
        "water_level": "OK",
        "drip_count": 3,
        "flame_lit": True,
    }

    bridge.handle_telemetry("d1", payload)

    assert db.alerts == []


def test_telemetry_refreshes_device_last_seen(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1060.0)
    payload = {
        "ts": "2026-08-11T10:20:00Z",
        "boiler_temp_c": 90.0,
        "gas_pressure_kpa": 2.8,
        "water_level": "OK",
        "drip_count": 3,
        "flame_lit": True,
    }

    bridge.handle_telemetry("d1", payload)

    assert db.last_seen == {"d1": 1060.0}
    assert db.offline_flags == [("d1", False)]


def test_device_silent_for_over_a_minute_is_flagged_offline(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"), last_seen={"d1": 1000.0})
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1070.0)

    bridge.check_offline()

    assert db.offline_flags == [("d1", True)]


def test_device_seen_recently_stays_online(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"), last_seen={"d1": 1000.0})
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1040.0)

    bridge.check_offline()

    assert db.offline_flags == []


def test_estimated_yield_accumulates_from_drips(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db, drip_ml=0.05)
    bridge.handle_telemetry("d1", {"ts": "10:00:00", "drip_count": 10, "boiler_temp_c": 95.0})
    bridge.handle_telemetry("d1", {"ts": "10:00:05", "drip_count": 15, "boiler_temp_c": 95.1})
    bridge.handle_telemetry("d1", {"ts": "10:00:10", "drip_count": 12, "boiler_temp_c": 95.0})

    assert db.estimates[-1]["estimated_yield_l"] == 0.00185
