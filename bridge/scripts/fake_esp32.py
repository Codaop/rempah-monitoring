#!/usr/bin/env python3
"""Fake ESP32 MQTT publisher - local dev / demo.

Publishes realistic telemetry to rempah/{FAKE_DEVICE_ID}/telemetry at 2-second
cadence and an initial retained state message to rempah/{FAKE_DEVICE_ID}/state.
Cadence is configurable via FEED_INTERVAL (seconds).
Replaces the direct-REST scripts/demo_feeder.py once the Bridge is running.

Usage (local mosquitto, no TLS):
    MQTT_BROKER=localhost MQTT_PORT=1883 \
    FAKE_DEVICE_ID=1a1a0000-0000-4000-8000-000000000001 \
    python bridge/scripts/fake_esp32.py

Usage (HiveMQ Cloud, TLS port 8883):
    MQTT_BROKER=xxx.hivemq.cloud MQTT_PORT=8883 \
    FAKE_DEVICE_USERNAME=dev-d1 FAKE_DEVICE_PASSWORD=... \
    FAKE_DEVICE_ID=1a1a0000-0000-4000-8000-000000000001 \
    python bridge/scripts/fake_esp32.py
"""
import json
import math
import os
import random
from pathlib import Path
import ssl
import threading
import time

import paho.mqtt.client as mqtt_client
from dotenv import load_dotenv

# Muat bridge/.env (path eksplisit relatif ke modul, tidak menimpa env yang
# sudah ada). Tanpa ini script jatuh ke default localhost:1883 dan gagal konek
# ke HiveMQ Cloud.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MQTT_BROKER      = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT        = int(os.environ.get("MQTT_PORT", "1883"))
TOPIC_ROOT       = os.environ.get("MQTT_TOPIC_ROOT", "command")
# Kredensial device: prioritas FAKE_DEVICE_*, fallback ke kredensial bridge
# (MQTT_USERNAME/PASSWORD) supaya demo jalan langsung dengan bridge/.env.
DEVICE_USERNAME  = os.environ.get("FAKE_DEVICE_USERNAME") or os.environ.get("MQTT_USERNAME", "rempah")
DEVICE_PASSWORD  = os.environ.get("FAKE_DEVICE_PASSWORD") or os.environ.get("MQTT_PASSWORD", "rempah123")
DEVICE_ID        = os.environ.get("FAKE_DEVICE_ID", "83271141-f523-4001-9d13-36506b848f8c")
INITIAL_MODE     = os.environ.get("FAKE_DEVICE_MODE", "DISTILLING")
INTERVAL         = float(os.environ.get("FEED_INTERVAL", "2"))

T0 = time.time()


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def telemetry_payload() -> dict:
    t = time.time()
    mins = (t - T0) / 60.0
    # Fluktuasi kecil (noise sensor) ditambahkan agar sparkline terlihat hidup
    # saat demo, tanpa mengubah tren fisik: massa turun perlahan, level air
    # turun perlahan, suhu boiler berosilasi di sekitar titik didih.
    return {
        "ts": _ts(),
        "boiler_temp_c": round(
            94.5 + 3.0 * math.sin(t / 45) + 0.5 * math.sin(t / 7) + random.uniform(-0.1, 0.1), 2
        ),
        # Sensor suhu kedua (pendingin/cooling): lebih dingin dari boiler,
        # naik perlahan seiring sistem berjalan.
        "cooling_temp_c": round(
            32.0 + 0.05 * mins + 2.0 * math.sin(t / 40) + random.uniform(-0.1, 0.1), 2
        ),
        # Sensor beban (load cell): massa tabung LPG menurun seiring konsumsi.
        # Asumsi tabung 15 kg + tare ~14 kg (total ~29 kg saat penuh).
        "gas_mass_kg": round(
            28.6 - 0.01 * mins + 0.05 * math.sin(t / 20) + random.uniform(-0.03, 0.03), 2
        ),
        "water_level": round(
            max(40.0, 66.0 - 0.02 * mins + 0.4 * math.sin(t / 25) + random.uniform(-0.2, 0.2)), 2
        ),
        "drip_count": max(1, int(6 + 4 * math.sin(t / 30))),
        "flame_lit": True,
    }


def state_payload(mode: str, cause: str = "detected", command_id: str | None = None) -> dict:
    p: dict = {"device_id": DEVICE_ID, "mode": mode, "cause": cause, "ts": _ts()}
    if command_id:
        p["command_id"] = command_id
    return p


def _publish_state(client: mqtt_client.Client, mode: str, cause: str, command_id: str | None = None) -> None:
    client.publish(
        f"{TOPIC_ROOT}/{DEVICE_ID}/state",
        json.dumps(state_payload(mode, cause, command_id)),
        qos=1,
        retain=True,
    )
    print(f"[{time.strftime('%H:%M:%S')}] state -> {mode} ({cause})")


def on_command(client: mqtt_client.Client, userdata, msg) -> None:
    """React to bridge commands so the full loop is demoable."""
    try:
        payload = json.loads(msg.payload)
    except json.JSONDecodeError:
        return
    action = payload.get("action")
    cid = payload.get("command_id")
    if action == "POWER_ON":
        _publish_state(client, "PREHEAT", f"command_executed:{cid}", cid)
        threading.Thread(target=lambda: (time.sleep(5), _publish_state(client, "DISTILLING", "detected")), daemon=True).start()
    elif action == "POWER_OFF":
        _publish_state(client, "IDLE", f"command_executed:{cid}", cid)
    elif action in ("ESTOP", "EMERGENCY_STOP"):
        _publish_state(client, "ESTOP", f"command_executed:{cid}", cid)


def main() -> None:
    client = mqtt_client.Client(
        callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
        client_id=f"fake-esp32-{DEVICE_ID[:8]}",
        protocol=mqtt_client.MQTTv5,
    )
    if DEVICE_USERNAME:
        client.username_pw_set(DEVICE_USERNAME, DEVICE_PASSWORD)
    if MQTT_PORT == 8883:
        client.tls_set_context(ssl.create_default_context())

    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    client.on_message = on_command
    client.subscribe(f"{TOPIC_ROOT}/{DEVICE_ID}/command", qos=1)

    # Announce initial retained state
    client.publish(
        f"{TOPIC_ROOT}/{DEVICE_ID}/state",
        json.dumps(state_payload(INITIAL_MODE)),
        qos=1,
        retain=True,
    )
    print(
        f"[fake-esp32] device={DEVICE_ID[:8]}... broker={MQTT_BROKER}:{MQTT_PORT} "
        f"mode={INITIAL_MODE} interval={INTERVAL}s"
    )

    while True:
        payload = telemetry_payload()
        client.publish(
            f"{TOPIC_ROOT}/{DEVICE_ID}/telemetry",
            json.dumps(payload),
            qos=1,
        )
        print(
            f"[{time.strftime('%H:%M:%S')}] telemetry "
            f"boiler={payload['boiler_temp_c']} C "
            f"gas={payload['gas_mass_kg']}kg "
            f"water={payload['water_level']}% "
            f"drip={payload['drip_count']}"
        )
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
