#!/usr/bin/env python3
"""E2E live check - menjalankan bridge + fake ESP32 nyata dan memverifikasi
seluruh pipeline sampai Supabase (ticket 18).

Fase:
  1. start bridge + fake_esp32 -> verifikasi telemetry masuk (sensor_logs bertambah)
  2. insert command POWER_OFF -> round-trip: command succeeded, batch close,
     batch_logs terisi (peak_temp / duration / yield_l)
  3. insert command EMERGENCY_STOP -> device_state = ESTOP, command succeeded
  4. stop fake_esp32 -> tunggu > OFFLINE_AFTER_S -> last_seen_at tidak berubah
     (dashboard akan menandai offline)

Usage:
    python bridge/scripts/e2e_live_check.py

Membaca kredensial dari bridge/.env (sama dengan bridge). Jangan dijalankan
bersamaan dengan instance bridge/fake_esp32 lain (duplikat client_id MQTT).
"""
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # bridge/
ENV = {}
for ln in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    ln = ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k, _, v = ln.partition("=")
        ENV[k.strip()] = v.strip()

URL = ENV["SUPABASE_URL"].rstrip("/")
KEY = ENV["SUPABASE_SERVICE_KEY"]
DEVICE = ENV.get("FAKE_DEVICE_ID", "1a1a0000-0000-4000-8000-000000000001")
PRODUCER = "0d0d0000-0000-4000-8000-000000000001"

BRIDGE_LOG = ROOT / "bridge_run.log"
FAKE_LOG = ROOT / "fake_run.log"


def rest(method: str, path: str, body: dict | None = None) -> list | dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        URL + path,
        data=data,
        method=method,
        headers={
            "apikey": KEY,
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_msg": e.read().decode()[:300]}


def table(path: str) -> list:
    res = rest("GET", path)
    return res if isinstance(res, list) else []


def short_id(v) -> str:
    return str(v)[:8] if v else str(v)


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def main() -> None:
    ok_all = True
    procs: list[subprocess.Popen] = []
    try:
        # -- Fase 1: start bridge + fake_esp32, tunggu telemetry -------------
        print("== Fase 1: start bridge + fake_esp32 (telemetry) ==")
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "rempah_bridge"],
            cwd=ROOT, stdout=open(BRIDGE_LOG, "w"), stderr=subprocess.STDOUT,
        ))
        time.sleep(10)
        procs.append(subprocess.Popen(
            [sys.executable, "scripts/fake_esp32.py"],
            cwd=ROOT, stdout=open(FAKE_LOG, "w"), stderr=subprocess.STDOUT,
        ))
        time.sleep(16)  # beberapa x interval telemetry 2s + margin

        count_before = len(table("/rest/v1/sensor_logs?select=id&limit=1000"))
        last_seen_before = table(
            "/rest/v1/devices?select=last_seen_at&id=eq." + DEVICE
        )
        ok = bool(count_before > 0 and last_seen_before and last_seen_before[0].get("last_seen_at"))
        ok_all &= check(
            "telemetry mengalir ke sensor_logs + last_seen_at ter-update",
            ok,
            f"rows={count_before} last_seen={last_seen_before[0].get('last_seen_at') if last_seen_before else None}",
        )

        # -- Fase 2: POWER_OFF -> round-trip + batch close --------------------
        print("== Fase 2: command POWER_OFF -> round-trip + batch close ==")
        res = rest("POST", "/rest/v1/commands", {
            "device_id": DEVICE,
            "action": "POWER_OFF",
            "expected_state": "DISTILLING",
            "producer_id": PRODUCER,
        })
        cmd_id = res[0]["id"] if isinstance(res, list) and res else None
        ok = bool(cmd_id)
        ok_all &= check("command POWER_OFF dibuat", ok, f"id={short_id(cmd_id)}")
        time.sleep(14)  # poll 2s + forward + device ack + close

        cmd = table("/rest/v1/commands?select=status&id=eq." + cmd_id)
        cmd_status = cmd[0]["status"] if cmd else "?"
        ok = cmd_status == "succeeded"
        ok_all &= check("command status = succeeded (device ack)", ok, cmd_status)

        batch = table(
            "/rest/v1/batches?select=status,ended_at&device_id=eq." + DEVICE
            + "&order=started_at.desc&limit=1"
        )
        bstatus = batch[0]["status"] if batch else "?"
        ok = bstatus == "completed"
        ok_all &= check("batch aktif ditutup", ok, bstatus)

        blog = table(
            "/rest/v1/batch_logs?select=batch_id,peak_temp,duration,yield_l"
        )
        latest = blog[0] if blog else {}
        ok = latest.get("duration") is not None and latest.get("yield_l") is not None
        ok_all &= check(
            "batch_logs terisi (duration + yield_l)",
            ok,
            f"duration={latest.get('duration')} yield_l={latest.get('yield_l')} peak={latest.get('peak_temp')}",
        )

        # -- Fase 3: EMERGENCY_STOP -> device_state ESTOP ---------------------
        print("== Fase 3: EMERGENCY_STOP -> device_state ESTOP ==")
        res = rest("POST", "/rest/v1/commands", {
            "device_id": DEVICE,
            "action": "EMERGENCY_STOP",
            "expected_state": None,
            "producer_id": PRODUCER,
        })
        cmd2 = res[0]["id"] if isinstance(res, list) and res else None
        ok = bool(cmd2)
        ok_all &= check("command EMERGENCY_STOP dibuat", ok, f"id={short_id(cmd2)}")
        time.sleep(12)

        cmd2_status = table("/rest/v1/commands?select=status&id=eq." + cmd2)
        c2s = cmd2_status[0]["status"] if cmd2_status else "?"
        ok = c2s == "succeeded"
        ok_all &= check("ESTOP command succeeded", ok, c2s)

        state = table("/rest/v1/device_state?select=mode&device_id=eq." + DEVICE)
        mode = state[0]["mode"] if state else "?"
        ok = mode == "ESTOP"
        ok_all &= check("device_state = ESTOP", ok, mode)

        # -- Fase 4: offline - hentikan fake_esp32, last_seen_at diam --------
        print("== Fase 4: offline - hentikan fake, tunggu window ==")
        fake = procs.pop(1)  # fake_esp32
        fake.terminate()
        try:
            fake.wait(timeout=10)
        except subprocess.TimeoutExpired:
            fake.kill()
        seen_stop = table("/rest/v1/devices?select=last_seen_at&id=eq." + DEVICE)
        last_at_stop = (seen_stop[0] or {}).get("last_seen_at") if seen_stop else None
        time.sleep(70)  # > OFFLINE_AFTER_S (60) + sweep interval (30)
        seen_later = table("/rest/v1/devices?select=last_seen_at&id=eq." + DEVICE)
        last_at_later = (seen_later[0] or {}).get("last_seen_at") if seen_later else None
        ok = bool(last_at_stop) and last_at_stop == last_at_later
        ok_all &= check(
            "last_seen_at tidak berubah setelah device berhenti (offline path)",
            ok,
            f"stop={last_at_stop} later={last_at_later}",
        )

    finally:
        for p in procs:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()

    print("=" * 60)
    print("HASIL E2E LIVE:", "SEMUA PASS" if ok_all else "ADA GAGAL")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
