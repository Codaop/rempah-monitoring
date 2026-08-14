"""Tests for SupabaseDbAdapter — telemetry storage without an active batch (ticket 33)."""

from typing import Any, Optional

from rempah_bridge.adapters.supabase_adapter import SupabaseDbAdapter


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    """Minimal chainable stand-in for the supabase-py query builder.

    Perilaku maybe_single() dibuat lebih "agresif" dari library asli:
    saat baris kosong, execute() mengembalikan None (bukan FakeResponse)
    — meniru bug nyata supabase-py 2.x yang membuat resp.data crash.
    """

    def __init__(self, rows: Optional[list] = None, null_on_empty: bool = False) -> None:
        self.rows = rows if rows is not None else []
        self.deleted: Optional[list] = None
        self._single = False
        self._null_on_empty = null_on_empty

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

    def execute(self):
        if self._single:
            if not self.rows:
                # supabase-py maybe_single() kosong → None mentah (bukan
                # FakeResponse) — reproduksi bug produksi yang pernah crash.
                return None if self._null_on_empty else FakeResponse(None)
            return FakeResponse(self.rows[0])
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
                self.tables[name] = FakeQuery(self._batch_rows, null_on_empty=True)
            elif name == "devices":
                self.tables[name] = FakeQuery(self._device_rows, null_on_empty=True)
            else:
                self.tables[name] = FakeQuery(null_on_empty=True)
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


def test_device_state_defaults_to_idle_when_row_missing() -> None:
    """maybe_single() kosong → None mentah (bug supabase-py 2.x) tidak boleh crash."""
    adapter, _ = _adapter(device_rows=[])

    state = adapter.device_state("d1")

    assert state.mode == "IDLE"


def test_note_first_contact_handles_missing_device_row() -> None:
    """Device tanpa baris (atau first_seen_at sudah terisi) tidak crash."""
    adapter, client = _adapter(device_rows=[])

    adapter.note_first_contact("d1", 1234567890.0)

    assert "alerts" not in client.tables or not client.tables["alerts"].inserted


def test_open_pending_batch_handles_missing_row() -> None:
    """Tidak ada batch pending → return diam-diam, tidak crash."""
    adapter, _ = _adapter(device_rows=[])

    adapter.open_pending_batch("d1", "2026-08-13T10:00:00Z")

    assert True  # sampai di sini tanpa exception sudah cukup


def test_close_active_batch_handles_missing_row() -> None:
    """Tidak ada batch aktif → return diam-diam, tidak crash."""
    adapter, _ = _adapter(device_rows=[])

    adapter.close_active_batch("d1", "2026-08-13T10:00:00Z")

    assert True  # sampai di sini tanpa exception sudah cukup
