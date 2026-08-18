#!/usr/bin/env python3
"""Demo telemetry feeder for REMPAH.

Pushes a realistic telemetry row for each demo device every 5 seconds and
keeps device_state / devices.last_seen_at fresh. Uses the service-role key
(bypasses RLS). Requires SUPABASE_SERVICE_KEY in the environment.

Replaces the real ESP32->MQTT->Bridge path for local/visual demos.
"""
import json
import math
import os
import random
import socket
import sys
import time
import urllib.request

socket.setdefaulttimeout(15)
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET] or res


socket.getaddrinfo = _ipv4_first

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qjroojbtquvrdgawxcrw.supabase.co").rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
INTERVAL = float(os.environ.get("FEED_INTERVAL", "5"))

PRODUCER_ID = "0d0d0000-0000-4000-8000-000000000001"
DEVICE_1 = "1a1a0000-0000-4000-8000-000000000001"   # Unit Kapulaga 1 - DISTILLING
DEVICE_2 = "2b2b0000-0000-4000-8000-000000000002"   # Unit Kapulaga 2 - IDLE
BATCH_ID = "4d4d0000-0000-4000-8000-000000000004"

T0 = time.time()


def request(method: str, path: str, body: dict | None = None) -> None:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{SUPABASE_URL}{path}",
        data=data,
        method=method,
        headers={
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"{method} {path} -> {resp.status}")
    elapsed = time.time() - start
    if elapsed > 1.0:
        print(f"[{time.strftime('%H:%M:%S')}] slow {method} {path}: {elapsed:.1f}s", flush=True)


def telemetry() -> list[dict]:
    t = time.time()
    mins = (t - T0) / 60.0
    # Fluktuasi kecil (noise sensor) agar sparkline terlihat hidup saat demo,
    # tanpa mengubah tren fisik: massa turun perlahan, level air turun perlahan.
    return [
        {
            "producer_id": PRODUCER_ID,
            "device_id": DEVICE_1,
            "batch_id": BATCH_ID,
            "boiler_temp_c": round(
                94.5 + 3.0 * math.sin(t / 45) + 0.5 * math.sin(t / 7) + random.uniform(-0.1, 0.1), 2
            ),
            "gas_mass_kg": round(
                28.6 - 0.01 * mins + 0.05 * math.sin(t / 20) + random.uniform(-0.03, 0.03), 2
            ),
            "water_level": round(
                max(40.0, 66.0 - 0.02 * mins + 0.4 * math.sin(t / 25) + random.uniform(-0.2, 0.2)), 2
            ),
            "drip_count": max(1, int(6 + 4 * math.sin(t / 30))),
            "flame_lit": True,
        },
        {
            "producer_id": PRODUCER_ID,
            "device_id": DEVICE_2,
            "batch_id": None,
            "boiler_temp_c": round(30 + 1.2 * math.sin(t / 60) + random.uniform(-0.2, 0.2), 2),
            "gas_mass_kg": round(
                28.9 - 0.005 * mins + 0.04 * math.sin(t / 22) + random.uniform(-0.02, 0.02), 2
            ),
            "water_level": round(70.0 + 0.3 * math.sin(t / 28) + random.uniform(-0.2, 0.2), 2),
            "drip_count": 0,
            "flame_lit": False,
        },
    ]


def main() -> None:
    if not SERVICE_KEY:
        sys.exit("SUPABASE_SERVICE_KEY is required")
    print(f"Feeding telemetry every {INTERVAL}s to {SUPABASE_URL}")
    while True:
        try:
            for row in telemetry():
                request("POST", "/rest/v1/sensor_logs", row)
            request(
                "PATCH",
                f"/rest/v1/device_state?device_id=eq.{DEVICE_1}",
                {"updated_at": datetime_iso()},
            )
            request(
                "PATCH",
                f"/rest/v1/devices?id=eq.{DEVICE_1}",
                {"last_seen_at": datetime_iso()},
            )
            print(f"[{time.strftime('%H:%M:%S')}] pushed {len(telemetry())} rows")
        except Exception as exc:  # keep the feeder alive across hiccups
            print(f"[{time.strftime('%H:%M:%S')}] error: {exc}")
        time.sleep(INTERVAL)


def datetime_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat()


if __name__ == "__main__":
    main()
