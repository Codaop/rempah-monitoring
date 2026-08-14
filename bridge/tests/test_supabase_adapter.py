"""Tests for SupabaseDbAdapter — telemetry storage without an active batch (ticket 33)."""

from typing import Any, Optional

from rempah_bridge.adapters.supabase_adapter import SupabaseDbAdapter


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    """Minimal chainable stand-in for the supabase-py query builder."""

    def __init__(self, rows: Optional[list] = None) -> None:
        self.rows = rows if rows is not None else []
        self.deleted: Optional[list] = None
        self._single = False

    def select(self, *cols: str) -> "FakeQuery":
        return self

    def eq(self, k: str, v: Any) -> "FakeQuery":
        return self

    def is_(self, k: str, v: Any) -> "FakeQuery":
        return self

    def lt(self, k: str, v: Any) -> "FakeQuery":
        return self

    def limit(self, n: int) -> "FakeQuery":
        return self

    def maybe_single(self) -> "FakeQuery":
        self._single = True
        return self

    def not_(self) -> "FakeQuery":
        return self

    def in_(self, k: str, v: Any) -> "FakeQuery":
        return self

    def execute(self) -> FakeResponse:
        if self._single:
            # supabase-py maybe_single() mengembalikan dict (atau None),
            # bukan list.
            return FakeResponse(self.rows[0] if self.rows else None)
        return FakeResponse(self.rows)

    def insert(self, row: dict) -> "FakeQuery":
        self.inserted = row
        return self

    def upsert(self, row: dict, on_conflict: str = "") -> "FakeQuery":
        self.inserted = row
        return self

    def update(self, data: dict) -> "FakeQuery":
        return self

    def delete(self) -> "FakeQuery":
        return self


class FakeClient:
    def __init__(self, batch_rows: Optional[list] = None, device_rows: Optional[list] = None) -> None:
        self._batch_rows = batch_rows or []
        self._device_rows = device_rows or []
        self.tables: dict[str, FakeQuery] = {}

    def table(self, name: str) -> FakeQuery:
        if name not in self.tables:
            if name == "batches":
                self.tables[name] = FakeQuery(self._batch_rows)
            elif name == "devices":
                self.tables[name] = FakeQuery(self._device_rows)
            else:
                self.tables[name] = FakeQuery()
        return self.tables[name]


def _adapter(batch_rows=None, device_rows=None) -> tuple[SupabaseDbAdapter, FakeClient]:
    client = FakeClient(batch_rows=batch_rows, device_rows=device_rows)
    adapter = SupabaseDbAdapter(client)
    return adapter, client


def test_insert_telemetry_without_active_batch_stores_row_with_null_batch() -> None:
    adapter, client = _adapter(
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )
    payload = {"ts": "2026-08-13T10:00:00Z", "boiler_temp_c": 90.0, "water_level": 60.0}

    adapter.insert_telemetry("d1", payload)

    inserted = client.tables["sensor_logs"].inserted
    assert inserted is not None
    assert inserted["device_id"] == "d1"
    assert inserted["producer_id"] == "p1"
    assert inserted["batch_id"] is None
    assert inserted["boiler_temp_c"] == 90.0


def test_insert_telemetry_with_active_batch_stores_batch_id() -> None:
    adapter, client = _adapter(
        batch_rows=[{"id": "b1", "target_yield_l": 5.0, "charge_mass_kg": 500.0}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )
    payload = {"ts": "2026-08-13T10:00:00Z", "boiler_temp_c": 95.0}

    adapter.insert_telemetry("d1", payload)

    inserted = client.tables["sensor_logs"].inserted
    assert inserted["batch_id"] == "b1"


def test_update_estimate_is_skipped_without_active_batch() -> None:
    adapter, client = _adapter(
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.update_estimate("d1", 0.01, "2026-08-13T10:00:00Z")

    assert "batch_logs" not in client.tables or not client.tables["batch_logs"].inserted
