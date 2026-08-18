#!/usr/bin/env python3
"""MQTT topic probe - verifies broker connectivity and topic traffic.

Connects with the same bridge/.env credentials, subscribes to rempah/# and
prints every message for a bounded window (default 15 s) or until Ctrl+C.
Answer: is the broker reachable, and is data flowing on the topics?

Usage:
    python bridge/scripts/mqtt_probe.py              # listen 15 s then exit
    python bridge/scripts/mqtt_probe.py --watch       # listen forever (Ctrl+C)
    python bridge/scripts/mqtt_probe.py --seconds 30
    python bridge/scripts/mqtt_probe.py --topic 'rempah/+/telemetry'
"""
import argparse
import os
from pathlib import Path
import ssl
import sys
import time
import uuid

import paho.mqtt.client as mqtt_client
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MQTT_BROKER   = os.environ.get("MQTT_BROKER", "")
MQTT_PORT     = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

TOPIC_ROOT = os.environ.get("MQTT_TOPIC_ROOT", "rempah")
TOPIC      = os.environ.get("MQTT_PROBE_TOPIC", f"{TOPIC_ROOT}/#")

SEEN: list[str] = []


def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
    if reason_code == 0:
        topic = userdata  # topic filter dipass lewat user_data_set()
        print(f"[probe] [OK] CONNECTED {MQTT_BROKER}:{MQTT_PORT} - subscribed {topic}")
        client.subscribe(topic, qos=1)
    else:
        print(f"[probe] [X] CONNECTION REFUSED reason_code={reason_code}")
        sys.exit(2)


def on_disconnect(client, userdata, flags, reason_code, properties=None) -> None:
    if reason_code != 0:
        print(f"[probe] ! unexpected disconnect reason_code={reason_code}")


def on_message(client, userdata, msg) -> None:
    text = msg.payload.decode(errors="replace")
    line = f"[{time.strftime('%H:%M:%S')}] {msg.topic} -> {text}"
    print(line)
    SEEN.append(line)


def main() -> None:
    ap = argparse.ArgumentParser(description="MQTT topic probe untuk REMPAH")
    ap.add_argument("--watch", action="store_true", help="subscribe terus-menerus (default: bounded window)")
    ap.add_argument("--seconds", type=int, default=15, help="durasi listen dalam mode bounded")
    ap.add_argument("--topic", default=TOPIC, help=f"topic filter MQTT (default: {TOPIC!r}, bisa dari env MQTT_PROBE_TOPIC)")
    args = ap.parse_args()

    if not MQTT_BROKER:
        print("[probe] MQTT_BROKER kosong - cek isi bridge/.env (salin dari .env.example).")
        sys.exit(2)

    client = mqtt_client.Client(
        callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
        # client_id unik per instance - dua probe/klien dengan id sama akan
        # saling tendang ("Session taken over") di broker.
        client_id=f"rempah-probe-{uuid.uuid4().hex[:8]}",
        protocol=mqtt_client.MQTTv5,
    )
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_PORT == 8883:
        client.tls_set_context(ssl.create_default_context())
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.user_data_set(args.topic)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
    except OSError as exc:
        print(f"[probe] [X] Tidak bisa konek ke {MQTT_BROKER}:{MQTT_PORT}: {exc}")
        sys.exit(2)
    client.loop_start()

    time.sleep(0.5)
    if not client.is_connected():
        print("[probe] [X] Tidak terhubung - cek kredensial/network/broker.")
        sys.exit(2)

    if args.watch:
        print("[probe] listening... Ctrl+C untuk berhenti")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print(f"[probe] mendengarkan {args.seconds} detik...")
        time.sleep(args.seconds)

    client.disconnect()
    client.loop_stop()

    if SEEN:
        print(f"[probe] [OK] {len(SEEN)} pesan diterima - topic aktif.")
    else:
        print(
            "[probe] ! Koneksi OK tapi tidak ada pesan dalam window - "
            "jalankan fake_esp32.py (atau kirim command dari dashboard) lalu ulangi."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
