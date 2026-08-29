from typing import Callable, List, Optional, Tuple

import pytest

from rempah_bridge.bridge import Bridge
from rempah_bridge.model import Command, DeviceState


class FakeMqtt:
    def __init__(self) -> None:
        self.published: List[Tuple[str, dict]] = []

    def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


class FakeDb:
    def __init__(
        self,
        state: DeviceState,
        last_seen: dict | None = None,
        known_devices: list[str] | None = None,
    ) -> None:
        self.state = state
        self.last_seen: dict[str, float] = last_seen or {}
        self.known_devices = set(known_devices) if known_devices is not None else {"d1"}
        self.offline_flags: List[Tuple[str, bool]] = []
        self.status_updates: List[Tuple[str, str]] = []
        self.telemetry: List[dict] = []
        self.state_updates: List[dict] = []
        self.alerts: List[dict] = []
        self.estimates: List[dict] = []
        self.batch_opens: List[Tuple[str, str]] = []
        self.batch_closes: List[Tuple[str, str]] = []
        self.batch_interrupts: List[Tuple[str, str]] = []
        self.batch_resumes: List[str] = []
        self.resume_result = True
        self.first_contacts: List[Tuple[str, str]] = []
        self.unknown_messages: List[dict] = []

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

    def note_first_contact(self, device_id: str, ts: float) -> None:
        self.first_contacts.append((device_id, ts))

    def is_known_device(self, device_id: str) -> bool:
        return device_id in self.known_devices

    def record_unknown_message(self, device_id: str, topic: str, payload: dict) -> None:
        self.unknown_messages.append(
            {"device_id": device_id, "topic": topic, "payload": payload}
        )

    def get_last_seen(self, device_id: str) -> Optional[float]:
        return self.last_seen.get(device_id)

    def list_devices(self) -> List[str]:
        return list(self.last_seen.keys())

    def set_offline(self, device_id: str, offline: bool) -> None:
        self.offline_flags.append((device_id, offline))

    def update_estimate(self, device_id: str, estimated_yield_l: float, ts: str) -> None:
        self.estimates.append(
            {"device_id": device_id, "estimated_yield_l": estimated_yield_l, "ts": ts}
        )

    def pending_commands(self) -> List[Command]:
        return []

    def open_pending_batch(self, device_id: str, ts: str) -> None:
        self.batch_opens.append((device_id, ts))

    def close_active_batch(self, device_id: str, ts: str) -> None:
        self.batch_closes.append((device_id, ts))

    def interrupt_active_batch(self, device_id: str, ts: str) -> None:
        self.batch_interrupts.append((device_id, ts))

    def resume_interrupted_batch(self, device_id: str) -> bool:
        self.batch_resumes.append(device_id)
        return self.resume_result

    def purge_old_sensor_logs(self) -> None:
        pass


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

    # Firmware hanya memahami "mati" — bridge menerjemahkan ESTOP ke sana.
    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c9", "action": "mati"})
    ]


def test_dashboard_emergency_stop_action_name_is_always_forwarded(mqtt: FakeMqtt) -> None:
    """Dashboard sends EMERGENCY_STOP; the bridge must not treat it as a stale command."""
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    estop = Command(id="c10", device_id="d1", action="EMERGENCY_STOP")

    bridge.process_command(estop)

    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c10", "action": "mati"})
    ]


def test_resume_batch_flips_batch_back_to_active_without_mqtt(mqtt: FakeMqtt) -> None:
    """RESUME_BATCH murni operasi DB: batch interrupted → active (ticket 59)."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c11", device_id="d1", action="RESUME_BATCH")

    bridge.process_command(command)

    assert db.batch_resumes == ["d1"]
    # Firmware tidak mengenal RESUME_BATCH → tidak ada publish MQTT.
    assert mqtt.published == []
    # Operasi DB selesai seketika → status langsung succeeded.
    assert db.status_updates == [("c11", "succeeded")]


def test_resume_batch_without_interrupted_batch_is_rejected(mqtt: FakeMqtt) -> None:
    """Tidak ada batch interrupted → RESUME_BATCH ditolak, tanpa publish."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    db.resume_result = False
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c12", device_id="d1", action="RESUME_BATCH")

    bridge.process_command(command)

    assert db.batch_resumes == ["d1"]
    assert mqtt.published == []
    assert db.status_updates == [("c12", "rejected")]


def test_forwarded_command_is_marked_dispatched(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c1", device_id="d1", action="STOP", expected_state="DISTILLING")

    bridge.process_command(command)

    assert db.status_updates == [("c1", "dispatched")]


def test_telemetry_message_is_persisted(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "ts": "2026-08-11T10:00:00Z",
        "boiler_temp_c": 102.4,
        "gas_mass_kg": 28.6,
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
        "gas_mass_kg": 28.6,
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
        "gas_mass_kg": 28.6,
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
        "gas_mass_kg": 28.6,
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
    # Ticket 58: device diam > ambang offline → batch active ikut ditandai
    # interrupted (idempoten via adapter).
    assert len(db.batch_interrupts) == 1
    assert db.batch_interrupts[0][0] == "d1"


def test_device_seen_recently_stays_online(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"), last_seen={"d1": 1000.0})
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1040.0)

    bridge.check_offline()

    assert db.offline_flags == []
    assert db.batch_interrupts == []


def test_estimated_yield_accumulates_from_drips(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db, drip_ml=0.05)
    bridge.handle_telemetry("d1", {"ts": "10:00:00", "drip_count": 10, "boiler_temp_c": 95.0})
    bridge.handle_telemetry("d1", {"ts": "10:00:05", "drip_count": 15, "boiler_temp_c": 95.1})
    bridge.handle_telemetry("d1", {"ts": "10:00:10", "drip_count": 12, "boiler_temp_c": 95.0})

    assert db.estimates[-1]["estimated_yield_l"] == 0.00185


def test_heating_transition_opens_pending_batch(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "PREHEAT",
        "cause": "detected",
        "ts": "2026-08-11T10:05:00Z",
    }

    bridge.handle_state(payload)

    assert db.batch_opens == [("d1", "2026-08-11T10:05:00Z")]


def test_terminal_transition_closes_active_batch(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "IDLE",
        "cause": "detected",
        "ts": "2026-08-11T11:00:00Z",
    }

    bridge.handle_state(payload)

    assert db.batch_closes == [("d1", "2026-08-11T11:00:00Z")]


def test_staying_in_heating_mode_does_not_reopen_batch(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "DISTILLING",
        "cause": "detected",
        "ts": "2026-08-11T10:06:00Z",
    }

    bridge.handle_state(payload)

    assert db.batch_opens == []


def test_draining_is_neither_heating_nor_terminal(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "d1",
        "mode": "DRAINING",
        "cause": "detected",
        "ts": "2026-08-11T11:00:00Z",
    }

    bridge.handle_state(payload)

    assert db.batch_opens == []
    assert db.batch_closes == []


def test_telemetry_records_first_contact(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1060.0)
    payload = {
        "ts": "2026-08-11T10:00:00Z",
        "boiler_temp_c": 95.0,
        "gas_mass_kg": 28.6,
        "water_level": "OK",
        "drip_count": 0,
        "flame_lit": True,
    }

    bridge.handle_telemetry("d1", payload)

    # first_seen_at memakai waktu terima bridge, bukan ts payload yang usang.
    assert db.first_contacts == [("d1", 1060.0)]


def test_state_records_first_contact(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1070.0)
    payload = {
        "device_id": "d1",
        "mode": "DISTILLING",
        "cause": "detected",
        "ts": "2026-08-11T10:05:00Z",
    }

    bridge.handle_state(payload)

    # first_seen_at memakai waktu terima bridge, bukan ts payload yang usang.
    assert db.first_contacts == [("d1", 1070.0)]


def test_power_on_is_translated_to_firmware_command_mulai(mqtt: FakeMqtt) -> None:
    """POWER_ON dari dashboard diterjemahkan menjadi "mulai" untuk firmware."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c1", device_id="d1", action="POWER_ON", expected_state="IDLE")

    bridge.process_command(command)

    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c1", "action": "mulai"})
    ]


def test_power_off_is_translated_to_firmware_command_mati(mqtt: FakeMqtt) -> None:
    """POWER_OFF dari dashboard diterjemahkan menjadi "mati" untuk firmware."""
    db = FakeDb(DeviceState(device_id="d1", mode="DISTILLING"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c2", device_id="d1", action="POWER_OFF", expected_state="DISTILLING")

    bridge.process_command(command)

    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c2", "action": "mati"})
    ]


def test_unknown_action_is_forwarded_unchanged(mqtt: FakeMqtt) -> None:
    """Action di luar tabel mapping (mis. perangkat kontrak penuh) tetap diteruskan."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    command = Command(id="c3", device_id="d1", action="REFILL", expected_state="IDLE")

    bridge.process_command(command)

    assert mqtt.published == [
        ("rempah/d1/command", {"command_id": "c3", "action": "REFILL"})
    ]


def test_telemetry_with_invalid_ts_falls_back_to_bridge_clock(mqtt: FakeMqtt) -> None:
    """`ts` payload yang rusak (angka non-timestamp) tidak boleh mematikan
    pipeline — diganti waktu terima bridge supaya insert tidak ditolak
    Postgres (ticket 49)."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1720000000.0)
    payload = {
        "ts": 955848,  # salah format — bukan ISO 8601
        "boiler_temp_c": 95.0,
        "gas_mass_kg": 28.6,
        "water_level": "OK",
        "drip_count": 0,
        "flame_lit": True,
    }

    bridge.handle_telemetry("d1", payload)

    expected_ts = "2024-07-03T09:46:40+00:00"
    assert db.telemetry == [{"device_id": "d1", **payload, "ts": expected_ts}]
    assert db.last_seen == {"d1": 1720000000.0}
    assert db.first_contacts == [("d1", 1720000000.0)]
    assert db.offline_flags == [("d1", False)]


def test_telemetry_with_clock_string_ts_falls_back(mqtt: FakeMqtt) -> None:
    """String waktu saja ("10:00:00") bukan datetime — harus di-fallback juga."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1720000000.0)
    payload = {"ts": "10:00:00", "boiler_temp_c": 95.0, "drip_count": 0}

    bridge.handle_telemetry("d1", payload)

    assert db.telemetry[0]["ts"] == "2024-07-03T09:46:40+00:00"


def test_state_with_invalid_ts_falls_back_to_bridge_clock(mqtt: FakeMqtt) -> None:
    """State message dengan ts rusak tetap diterapkan memakai waktu terima bridge."""
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db, clock=lambda: 1720000000.0)
    payload = {
        "device_id": "d1",
        "mode": "PREHEAT",
        "cause": "detected",
        "ts": "955848",
    }

    bridge.handle_state(payload)

    expected_ts = "2024-07-03T09:46:40+00:00"
    assert db.state_updates == [{"device_id": "d1", "mode": "PREHEAT", "ts": expected_ts}]
    assert db.batch_opens == [("d1", expected_ts)]


def test_telemetry_from_unknown_device_is_recorded_not_persisted(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "ts": "2026-08-11T10:00:00Z",
        "boiler_temp_c": 95.0,
        "gas_mass_kg": 28.6,
        "water_level": "OK",
        "drip_count": 0,
        "flame_lit": True,
    }

    bridge.handle_telemetry("ghost", payload)

    assert db.unknown_messages == [
        {"device_id": "ghost", "topic": "rempah/ghost/telemetry", "payload": payload}
    ]
    assert db.telemetry == []
    assert db.last_seen == {}
    assert db.first_contacts == []


def test_state_from_unknown_device_is_recorded_not_applied(mqtt: FakeMqtt) -> None:
    db = FakeDb(DeviceState(device_id="d1", mode="IDLE"))
    bridge = Bridge(mqtt=mqtt, db=db)
    payload = {
        "device_id": "ghost",
        "mode": "DISTILLING",
        "cause": "detected",
        "ts": "2026-08-11T10:05:00Z",
    }

    bridge.handle_state(payload)

    assert db.unknown_messages == [
        {"device_id": "ghost", "topic": "rempah/ghost/state", "payload": payload}
    ]
    assert db.state_updates == []
    assert db.first_contacts == []
