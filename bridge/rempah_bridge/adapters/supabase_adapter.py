"""Supabase adapter — implements DbPort using the service-role key (bypasses RLS)."""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import Client

from rempah_bridge.model import Command, DeviceState

logger = logging.getLogger(__name__)


class SupabaseDbAdapter:
    def __init__(
        self,
        client: Client,
        yield_ratio_l_per_kg: float = 0.01,
        drip_ml: float = 0.05,
    ) -> None:
        self._client = client
        self._yield_ratio_l_per_kg = yield_ratio_l_per_kg
        self._drip_ml = drip_ml
        # device_id → producer_id, populated lazily
        self._producer_cache: dict[str, str] = {}
        # device_id → (estimated_yield_l, epoch_float) for ETA computation
        self._estimate_history: dict[str, tuple[float, float]] = {}

    # ── Telemetry ────────────────────────────────────────────────────────────

    def insert_telemetry(self, device_id: str, payload: dict) -> None:
        # Telemetry selalu disimpan — dengan batch_id NULL saat tidak ada batch
        # aktif (ticket 33) agar dashboard bisa menampilkan nilai real-time
        # perangkat di luar batch (cek kesiapan, monitoring pasif).
        batch = self._active_batch(device_id)
        producer_id = self._resolve_producer(device_id)
        row = {
            "batch_id": batch["id"] if batch else None,
            "device_id": device_id,
            "producer_id": producer_id,
            **payload,
        }
        self._client.table("sensor_logs").insert(row).execute()

    # ── Device state ─────────────────────────────────────────────────────────

    def device_state(self, device_id: str) -> DeviceState:
        resp = (
            self._client.table("device_state")
            .select("mode")
            .eq("device_id", device_id)
            .maybe_single()
            .execute()
        )
        mode = resp.data["mode"] if resp.data else "IDLE"
        return DeviceState(device_id=device_id, mode=mode)

    def set_device_state(self, device_id: str, mode: str, ts: str) -> None:
        producer_id = self._resolve_producer(device_id)
        self._client.table("device_state").upsert(
            {
                "device_id": device_id,
                "mode": mode,
                "updated_at": ts,
                "producer_id": producer_id,
            },
            on_conflict="device_id",
        ).execute()

    # ── Device presence ──────────────────────────────────────────────────────

    def set_last_seen(self, device_id: str, ts: float) -> None:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        self._client.table("devices").update({"last_seen_at": dt}).eq("id", device_id).execute()

    def get_last_seen(self, device_id: str) -> Optional[float]:
        resp = (
            self._client.table("devices")
            .select("last_seen_at")
            .eq("id", device_id)
            .maybe_single()
            .execute()
        )
        if not resp.data or not resp.data.get("last_seen_at"):
            return None
        return datetime.fromisoformat(resp.data["last_seen_at"]).timestamp()

    def set_offline(self, device_id: str, offline: bool) -> None:
        # The dashboard derives offline status from last_seen_at; no separate column needed.
        # This method intentionally a no-op — set_last_seen carries the information.
        pass

    def note_first_contact(self, device_id: str, ts: float) -> None:
        """Handshake koneksi pertama (ticket 41): catat first_seen_at sekali.

        Dipanggil saat telemetry/state pertama dari sebuah device. Jika
        first_seen_at belum terisi, tulis timestamp ini dan buat alert
        "perangkat terhubung pertama kali" — penanda provisioning berhasil.
        Reconnect tidak menimpa nilai yang sudah ada. `ts` adalah waktu terima
        bridge (epoch float), diformat ke ISO di sini agar konsisten dengan
        set_last_seen dan tidak bergantung pada `ts` payload yang bisa usang.
        """
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        try:
            resp = (
                self._client.table("devices")
                .select("first_seen_at, name")
                .eq("id", device_id)
                .maybe_single()
                .execute()
            )
            if not resp.data or resp.data.get("first_seen_at"):
                return
            self._client.table("devices").update(
                {"first_seen_at": dt}
            ).eq("id", device_id).execute()
            name = resp.data.get("name") or device_id[:8]
            producer_id = self._resolve_producer(device_id)
            self._client.table("alerts").insert(
                {
                    "device_id": device_id,
                    "producer_id": producer_id,
                    "kind": "device_first_seen",
                    "value": 0.0,
                    "ts": dt,
                }
            ).execute()
            logger.info("first contact recorded for device %s (%s)", device_id[:8], name)
        except Exception as exc:
            logger.warning("note_first_contact failed for %s: %s", device_id, exc)

    def list_devices(self) -> list[str]:
        resp = self._client.table("devices").select("id").execute()
        return [r["id"] for r in (resp.data or [])]

    def is_known_device(self, device_id: str) -> bool:
        return self._resolve_producer(device_id) is not None

    def record_unknown_message(self, device_id: str, topic: str, payload: dict) -> None:
        """Catat pesan dari device_id yang tidak terdaftar (ticket 43).

        Tabel `alerts` tidak bisa dipakai (FK device_id NOT NULL ke devices),
        jadi kejadian disimpan di `unknown_messages` agar operator bisa
        mendiagnosis device liar / salah konfigurasi dari dashboard.
        """
        try:
            self._client.table("unknown_messages").insert(
                {
                    "device_id": device_id,
                    "topic": topic,
                    "payload": payload,
                }
            ).execute()
            logger.warning("Unknown device %s published to %s — recorded", device_id[:8], topic)
        except Exception as exc:
            logger.warning("record_unknown_message failed: %s", exc)

    # ── Commands ─────────────────────────────────────────────────────────────

    def mark_command(self, command_id: str, status: str) -> None:
        self._client.table("commands").update({"status": status}).eq("id", command_id).execute()

    def pending_commands(self) -> list[Command]:
        resp = (
            self._client.table("commands")
            .select("id, device_id, action, expected_state")
            .eq("status", "pending")
            .limit(50)
            .execute()
        )
        return [
            Command(
                id=r["id"],
                device_id=r["device_id"],
                action=r["action"],
                expected_state=r.get("expected_state"),
            )
            for r in (resp.data or [])
        ]

    # ── Alerts ───────────────────────────────────────────────────────────────

    def insert_alert(self, device_id: str, kind: str, value: float, ts: str) -> None:
        producer_id = self._resolve_producer(device_id)
        try:
            self._client.table("alerts").insert(
                {
                    "device_id": device_id,
                    "producer_id": producer_id,
                    "kind": kind,
                    "value": value,
                    "ts": ts,
                }
            ).execute()
        except Exception as exc:
            logger.warning("insert_alert failed (table may not exist yet): %s", exc)

    # ── Estimates ────────────────────────────────────────────────────────────

    def update_estimate(self, device_id: str, estimated_yield_l: float, ts: str) -> None:
        batch = self._active_batch(device_id)
        if batch is None:
            return
        estimated_finish_at = self._compute_eta(device_id, estimated_yield_l, ts, batch)
        self._client.table("batch_logs").upsert(
            {
                "batch_id": batch["id"],
                "producer_id": self._resolve_producer(device_id),
                "estimated_yield": estimated_yield_l,
                "estimated_finish_at": estimated_finish_at,
            },
            on_conflict="batch_id",
        ).execute()

    # ── Batch lifecycle ──────────────────────────────────────────────────────

    def open_pending_batch(self, device_id: str, ts: str) -> None:
        """Flip the dashboard-created pending batch to active on heating start."""
        resp = (
            self._client.table("batches")
            .select("id, charge_mass_kg")
            .eq("device_id", device_id)
            .eq("status", "pending")
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            logger.debug("No pending batch for device %s; nothing to open", device_id)
            return
        charge_kg = float(resp.data.get("charge_mass_kg") or 0)
        target_yield_l = round(charge_kg * self._yield_ratio_l_per_kg, 4)
        self._client.table("batches").update(
            {"status": "active", "started_at": ts, "target_yield_l": target_yield_l}
        ).eq("id", resp.data["id"]).execute()
        logger.info(
            "batch %s opened (charge=%skg, target=%sL)",
            resp.data["id"][:8], charge_kg, target_yield_l,
        )

    def close_active_batch(self, device_id: str, ts: str) -> None:
        """Close the active batch and finalize its batch_logs aggregate."""
        resp = (
            self._client.table("batches")
            .select("id, started_at")
            .eq("device_id", device_id)
            .eq("status", "active")
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not resp.data:
            logger.debug("No active batch for device %s; nothing to close", device_id)
            return
        batch_id = resp.data["id"]
        # PostgREST di project ini menolak aggregate functions (PGRST123), jadi
        # MAX/SUM dihitung di Python dari baris-baris sensor batch.
        rows = (
            self._client.table("sensor_logs")
            .select("boiler_temp_c,drip_count")
            .eq("batch_id", batch_id)
            .execute()
        )
        temps = [float(r["boiler_temp_c"]) for r in (rows.data or []) if r.get("boiler_temp_c") is not None]
        drips = [float(r.get("drip_count") or 0) for r in (rows.data or [])]
        peak_temp = max(temps) if temps else 0.0
        total_drips = sum(drips)
        yield_l = round(total_drips * self._drip_ml / 1000, 4)
        duration_s = 0.0
        try:
            start = datetime.fromisoformat(resp.data["started_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            duration_s = max(0.0, (end - start).total_seconds())
        except (ValueError, AttributeError):
            pass
        self._client.table("batches").update(
            {"status": "completed", "ended_at": ts}
        ).eq("id", batch_id).execute()
        self._client.table("batch_logs").upsert(
            {
                "batch_id": batch_id,
                "producer_id": self._resolve_producer(device_id),
                "peak_temp": peak_temp,
                "duration": f"PT{int(duration_s)}S",  # interval (ISO 8601)
                "yield_l": yield_l,
            },
            on_conflict="batch_id",
        ).execute()
        logger.info(
            "batch %s closed: peak=%s°C duration=%ss yield=%sL",
            batch_id[:8], peak_temp, duration_s, yield_l,
        )

    # ── Retention ────────────────────────────────────────────────────────────

    def purge_old_sensor_logs(self) -> None:
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
        try:
            closed = (
                self._client.table("batches")
                .select("id")
                .not_.is_("ended_at", None)
                .lt("ended_at", cutoff)
                .execute()
            )
            batch_ids = [r["id"] for r in (closed.data or [])]
            if batch_ids:
                self._client.table("sensor_logs").delete().in_("batch_id", batch_ids).execute()
                logger.info("Purged sensor_logs for %d closed batches before %s", len(batch_ids), cutoff)
            # Baris idle (batch_id NULL) yang berumur >7 hari ikut dibersihkan
            # (ticket 27) — didukung partial index sensor_logs_idle_ts_idx.
            idle = (
                self._client.table("sensor_logs")
                .delete()
                .is_("batch_id", None)
                .lt("ts", cutoff)
                .execute()
            )
            idle_count = len(idle.data or [])
            if idle_count:
                logger.info("Purged %d idle sensor_logs rows before %s", idle_count, cutoff)
        except Exception as exc:
            logger.warning("purge_old_sensor_logs failed: %s", exc)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _active_batch(self, device_id: str) -> Optional[dict]:
        resp = (
            self._client.table("batches")
            .select("id, target_yield_l, charge_mass_kg")
            .eq("device_id", device_id)
            .eq("status", "active")
            .limit(1)
            .maybe_single()
            .execute()
        )
        return resp.data

    def _resolve_producer(self, device_id: str) -> Optional[str]:
        if device_id not in self._producer_cache:
            resp = (
                self._client.table("devices")
                .select("producer_id")
                .eq("id", device_id)
                .maybe_single()
                .execute()
            )
            if resp.data:
                self._producer_cache[device_id] = resp.data["producer_id"]
        return self._producer_cache.get(device_id)

    def _compute_eta(
        self,
        device_id: str,
        estimated_yield_l: float,
        ts: str,
        batch: dict,
    ) -> Optional[str]:
        """Estimate finish time from drip-yield rate against batch target."""
        try:
            target = float(batch.get("target_yield_l") or 0)
            if not target or estimated_yield_l >= target:
                return None
            try:
                now_epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except (ValueError, AttributeError):
                now_epoch = time.time()

            prev = self._estimate_history.get(device_id)
            self._estimate_history[device_id] = (estimated_yield_l, now_epoch)

            if prev is None:
                return None
            prev_yield, prev_epoch = prev
            delta_yield = estimated_yield_l - prev_yield
            delta_time = now_epoch - prev_epoch
            if delta_time <= 0 or delta_yield <= 0:
                return None

            rate = delta_yield / delta_time  # L/s
            remaining = target - estimated_yield_l
            finish_epoch = now_epoch + remaining / rate
            eta = datetime.fromtimestamp(finish_epoch, tz=timezone.utc)
            return eta.isoformat()
        except Exception as exc:
            logger.debug("ETA computation skipped: %s", exc)
            return None
