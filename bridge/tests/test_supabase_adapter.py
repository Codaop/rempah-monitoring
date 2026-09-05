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
        self._last_query: dict[str, FakeQuery] = {}

    def table(self, name: str) -> FakeQuery:
        # Return fresh FakeQuery each time to avoid state pollution
        # But track the last one for test assertions
        if name == "batches":
            q = FakeQuery(self._batch_rows, null_on_empty=True)
        elif name == "devices":
            q = FakeQuery(self._device_rows, null_on_empty=True)
        elif name == "sensor_logs":
            q = FakeQuery(self._sensor_rows, null_on_empty=True)
        else:
            q = FakeQuery(null_on_empty=True)
        self._last_query[name] = q
        return q

    def last_query(self, name: str) -> FakeQuery:
        return self._last_query.get(name)


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

    inserted = client.last_query("sensor_logs").inserted
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

    inserted = client.last_query("sensor_logs").inserted
    assert inserted["batch_id"] == "b1"


def test_update_estimate_is_skipped_without_active_batch() -> None:
    adapter, client = _adapter(
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.update_estimate("d1", 0.01, "2026-08-13T10:00:00Z")

    q = client.last_query("batch_logs"); assert q is None or not q.inserted


def test_device_state_defaults_to_idle_when_row_missing() -> None:
    """maybe_single() kosong → None mentah (bug supabase-py 2.x) tidak boleh crash."""
    adapter, _ = _adapter(device_rows=[])

    state = adapter.device_state("d1")

    assert state.mode == "IDLE"


def test_note_first_contact_handles_missing_device_row() -> None:
    """Device tanpa baris (atau first_seen_at sudah terisi) tidak crash."""
    adapter, client = _adapter(device_rows=[])

    adapter.note_first_contact("d1", 1234567890.0)

    q = client.last_query("alerts"); assert q is None or not q.inserted


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

    log = client.last_query("batch_logs").inserted
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

    log = client.last_query("batch_logs").inserted
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

    updated = client.last_query("batches").updated
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

    assert client.last_query("batches").updated is None


def test_interrupt_active_batch_no_active_batch_noop() -> None:
    """Device tanpa batch sama sekali → no-op (tidak crash)."""
    adapter, client = _adapter(
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    adapter.interrupt_active_batch("d1", "2026-08-13T11:00:00Z")

    assert client.last_query("batches").updated is None


def test_resume_interrupted_batch_marks_batch_active() -> None:
    """Batch interrupted di-set active + interrupted_at dibersihkan (ticket 59)."""
    adapter, client = _adapter(
        batch_rows=[{"id": "b1", "status": "interrupted"}],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    resumed = adapter.resume_interrupted_batch("d1")

    assert resumed is True
    updated = client.last_query("batches").updated
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

    updated = client.last_query("batches").updated
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
    assert client.last_query("batches").updated is None


def test_upsert_pending_batch_from_device_creates_new_batch() -> None:
    """Device mengirim 'mulai' dengan berat_muatan → create pending batch dengan charge_source=device."""
    adapter, client = _adapter(
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    success = adapter.upsert_pending_batch_from_device("d1", 2.5, "2026-08-13T10:00:00Z")

    assert success is True
    inserted = client.last_query("batches").inserted
    assert inserted is not None
    assert inserted["device_id"] == "d1"
    assert inserted["producer_id"] == "p1"
    assert inserted["charge_mass_kg"] == 2.5
    assert inserted["status"] == "pending"
    assert inserted["charge_source"] == "device"
    assert inserted["created_at"] == "2026-08-13T10:00:00Z"
    assert inserted["updated_at"] == "2026-08-13T10:00:00Z"


def test_upsert_pending_batch_from_device_updates_existing_pending() -> None:
    """Dashboard sudah create pending batch → device update charge_mass_kg (device wins)."""
    adapter, client = _adapter(
        batch_rows=[
            {"id": "b1", "device_id": "d1", "status": "pending", "charge_mass_kg": 1.0, "charge_source": "dashboard"}
        ],
        device_rows=[{"id": "d1", "producer_id": "p1"}],
    )

    success = adapter.upsert_pending_batch_from_device("d1", 3.5, "2026-08-13T11:00:00Z")

    assert success is True
    updated = client.last_query("batches").updated
    assert updated is not None
    assert updated["charge_mass_kg"] == 3.5
    assert updated["charge_source"] == "device"
    assert updated["updated_at"] == "2026-08-13T11:00:00Z"
    # created_at tidak diubah


def test_upsert_pending_batch_from_device_unknown_device_returns_false() -> None:
    """Device tidak dikenal di tabel devices → False, tidak create batch."""
    adapter, client = _adapter(device_rows=[])

    success = adapter.upsert_pending_batch_from_device("unknown", 2.5, "2026-08-13T10:00:00Z")

    assert success is False
    q = client.last_query("batches")
    assert q is None  # batches table never accessed


def test_upsert_pending_batch_from_device_handles_missing_charge_source_column() -> None:
    """Jika kolom charge_source belum ada di DB, fallback tanpa charge_source (graceful degradation)."""
    # Shared state to track calls across multiple FakeQuery instances
    class SharedState:
        def __init__(self):
            self.call_count = 0
            self.inserted = None
            self.updated = None

    shared = SharedState()

    class FakeQueryWithError:
        def select(self, *cols): return self
        def eq(self, k, v): return self
        def limit(self, n): return self
        def maybe_single(self): return self

        def execute(self):
            shared.call_count += 1
            if shared.call_count == 1:
                # First call: select existing pending batch - return None (no existing)
                return None
            # Retry insert: return fake inserted row with ID
            return FakeResponse([{"id": "new-batch-id"}])

        def insert(self, row):
            shared.inserted = row
            shared.call_count += 1
            # First insert attempt with charge_source fails
            if shared.call_count == 2:
                raise Exception("column charge_source does not exist")
            return self

        def update(self, data):
            shared.updated = data
            shared.call_count += 1
            if shared.call_count == 2:
                raise Exception("column charge_source does not exist")
            return self

    class FakeClientWithError:
        def table(self, name):
            return FakeQueryWithError()

    from rempah_bridge.adapters.supabase_adapter import SupabaseDbAdapter
    adapter = SupabaseDbAdapter(FakeClientWithError())
    adapter._resolve_producer = lambda d: "p1"  # mock

    success = adapter.upsert_pending_batch_from_device("d1", 2.5, "2026-08-13T10:00:00Z")

    # Should succeed on retry without charge_source
    assert success is True
