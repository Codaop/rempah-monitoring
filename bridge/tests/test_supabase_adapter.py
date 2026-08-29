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
        self._filters: list[tuple[str, Any]] = []

    def select(self, *cols: str) -> "FakeQuery":
        return self

    def eq(self, k: str, v: Any) -> "FakeQuery":
        # Baris yang punya key tsb dengan nilai berbeda disaring; baris tanpa
        # key tersebut lolos (konvensi fixture: status sering dihilangkan).
        self._filters.append((k, v))
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
        filtered = list(self.rows)
        for k, v in self._filters:
            filtered = [r for r in filtered if r.get(k) is None or r.get(k) == v]
        if self._single:
            if not filtered:
                # supabase-py maybe_single() kosong → None mentah (bukan
                # FakeResponse) — reproduksi bug produksi yang pernah crash.
                return None if self._null_on_empty else FakeResponse(None)
            return FakeResponse(filtered[0])
        return FakeResponse(filtered)

    def insert(self, row: dict) -> "FakeQuery":
        self.inserted = row
        return self

    def upsert(self, row: dict, on_conflict: str = "") -> "FakeQuery":
        self.inserted = row
        return self

    def update(self, data: dict) -> "FakeQuery":
        self._update_data = data
        return self

    @property
    def updated(self) -> Optional[dict]:
        return getattr(self, "_update_data", None)

    def delete(self) -> "FakeQuery":
        return self


class FakeClient:
    def __init__(
        self,
        batch_rows: Optional[list] = None,
        device_rows: Optional[list] = None,
        sensor_rows: Optional[list] = None,
    ) -> None:
        self._batch_rows = batch_rows or []
        self._device_rows = device_rows or []
        self._sensor_rows = sensor_rows or []
        self.tables: dict[str, FakeQuery] = {}

    def table(self, name: str) -> FakeQuery:
        if name not in self.tables:
            if name == "batches":
                self.tables[name] = FakeQuery(self._batch_rows, null_on_empty=True)
            elif name == "devices":
                self.tables[name] = FakeQuery(self._device_rows, null_on_empty=True)
            elif name == "sensor_logs":
                self.tables[name] = FakeQuery(self._sensor_rows, null_on_empty=True)
            else:
                self.tables[name] = FakeQuery(null_on_empty=True)
        return self.tables[name]


def _adapter(batch_rows=None, device_rows=None, sensor_rows=None) -> tuple[SupabaseDbAdapter, FakeClient]:
    client = FakeClient(batch_rows=batch_rows, device_rows=device_rows, sensor_rows=sensor_rows)
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


def test_close_active_batch_records_gas_usage() -> None:
    """Penggunaan gas dihitung dari selisih massa awal vs akhir batch (ticket 51)."""
    adapter, client = _adapter(
        batch_rows=[
            {
                "id": "b1",
                "started_at": "2026-08-13T10:00:00Z",
                "charge_mass_kg": 5.0,
            }
        ],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
        sensor_rows=[
            {"boiler_temp_c": 90.0, "drip_count": 2, "gas_mass_kg": 28.6},
            {"boiler_temp_c": 95.0, "drip_count": 3, "gas_mass_kg": 28.1},
            {"boiler_temp_c": 97.0, "drip_count": 4, "gas_mass_kg": 27.9},
        ],
    )

    adapter.close_active_batch("d1", "2026-08-13T11:00:00Z")

    log = client.tables["batch_logs"].inserted
    assert log is not None
    assert log["gas_start_kg"] == 28.6
    assert log["gas_end_kg"] == 27.9
    assert log["gas_used_kg"] == round(28.6 - 27.9, 3)


def test_close_active_batch_gas_usage_none_when_no_gas_data() -> None:
    """Tanpa data gas di sensor_logs, kolom gas di batch_logs bernilai None."""
    adapter, client = _adapter(
        batch_rows=[
            {
                "id": "b2",
                "started_at": "2026-08-13T10:00:00Z",
                "charge_mass_kg": 5.0,
            }
        ],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
        sensor_rows=[
            {"boiler_temp_c": 90.0, "drip_count": 2, "gas_mass_kg": None},
            {"boiler_temp_c": 95.0, "drip_count": 3, "gas_mass_kg": None},
        ],
    )

    adapter.close_active_batch("d1", "2026-08-13T11:00:00Z")

    log = client.tables["batch_logs"].inserted
    assert log is not None
    assert log["gas_start_kg"] is None
    assert log["gas_end_kg"] is None
    assert log["gas_used_kg"] is None


def test_interrupt_active_batch_marks_batch_interrupted() -> None:
    """Batch active di-set interrupted + interrupted_at (ticket 58)."""
    adapter, client = _adapter(
        batch_rows=[{"id": "b1"}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.interrupt_active_batch("d1", "2026-08-13T11:00:00Z")

    updated = client.tables["batches"].updated
    assert updated is not None
    assert updated["status"] == "interrupted"
    assert updated["interrupted_at"] == "2026-08-13T11:00:00Z"


def test_interrupt_active_batch_idempotent_without_active_batch() -> None:
    """Tidak ada batch active → tidak melakukan apa-apa, tidak crash."""
    adapter, client = _adapter(
        batch_rows=[{"id": "b1", "status": "interrupted"}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.interrupt_active_batch("d1", "2026-08-13T11:00:00Z")

    assert client.tables["batches"].updated is None


def test_interrupt_active_batch_no_active_batch_noop() -> None:
    """Device tanpa batch sama sekali → no-op (tidak crash)."""
    adapter, client = _adapter(
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.interrupt_active_batch("d1", "2026-08-13T11:00:00Z")

    assert client.tables["batches"].updated is None


def test_resume_interrupted_batch_marks_batch_active() -> None:
    """Batch interrupted di-set active + interrupted_at dibersihkan (ticket 59)."""
    adapter, client = _adapter(
        batch_rows=[{"id": "b1", "status": "interrupted"}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    resumed = adapter.resume_interrupted_batch("d1")

    assert resumed is True
    updated = client.tables["batches"].updated
    assert updated is not None
    assert updated["status"] == "active"
    assert updated["interrupted_at"] is None


def test_resume_interrupted_batch_keeps_started_at_untouched() -> None:
    """started_at tidak diubah — durasi total jujur dari awal proses (ticket 59)."""
    adapter, client = _adapter(
        batch_rows=[{"id": "b1", "status": "interrupted", "started_at": "2026-08-13T10:00:00Z"}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.resume_interrupted_batch("d1")

    updated = client.tables["batches"].updated
    assert updated is not None
    assert "started_at" not in updated  # tidak disentuh sama sekali


def test_resume_interrupted_batch_returns_false_without_interrupted_batch() -> None:
    """Tidak ada batch interrupted → False, tanpa update (ticket 59)."""
    adapter, client = _adapter(
        batch_rows=[{"id": "b1", "status": "active"}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    resumed = adapter.resume_interrupted_batch("d1")

    assert resumed is False
    assert client.tables["batches"].updated is None
