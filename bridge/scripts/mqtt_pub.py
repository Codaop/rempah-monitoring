#!/usr/bin/env python3
"""MQTT test publisher - publish one message (or a loop) to any topic.

Pasangan dari mqtt_probe.py: untuk memverifikasi bahwa publish masuk ke broker
dan diterima subscriber (mis. probe yang sedang listen di topic yang sama).

Usage:
    python bridge/scripts/mqtt_pub.py --topic "topik/device1" --message '{"temp": 95.2}'
    python bridge/scripts/mqtt_pub.py --topic "topik/device1" --message 'hello' --retain
    python bridge/scripts/mqtt_pub.py --topic "topik/device1" --message '{"temp": 95.2}' --loop 5
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


def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
    if reason_code == 0:
        print(f"[pub] [OK] CONNECTED {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"[pub] [X] CONNECTION REFUSED reason_code={reason_code}")
        sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description="MQTT test publisher untuk REMPAH")
    ap.add_argument("--topic", required=True, help="topic tujuan")
    ap.add_argument("--message", required=True, help="payload (boleh JSON/teks)")
    ap.add_argument("--retain", action="store_true", help="set retain flag (probe langsung menerimanya saat subscribe)")
    ap.add_argument("--loop", type=float, default=0, help="publish berulang tiap N detik (0 = sekali saja)")
    args = ap.parse_args()

    if not MQTT_BROKER:
        print("[pub] MQTT_BROKER kosong - cek isi bridge/.env (salin dari .env.example).")
        sys.exit(2)

    client = mqtt_client.Client(
        callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
        # client_id unik per instance - dua klien dengan id sama saling tendang.
        client_id=f"rempah-pub-{uuid.uuid4().hex[:8]}",
        protocol=mqtt_client.MQTTv5,
    )
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_PORT == 8883:
        client.tls_set_context(ssl.create_default_context())
    client.on_connect = on_connect

    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
    except OSError as exc:
        print(f"[pub] [X] Tidak bisa konek ke {MQTT_BROKER}:{MQTT_PORT}: {exc}")
        sys.exit(2)
    client.loop_start()

    time.sleep(0.5)
    if not client.is_connected():
        print("[pub] [X] Tidak terhubung.")
        sys.exit(2)

    payload = args.message.encode()
    while True:
        info = client.publish(args.topic, payload, qos=1, retain=args.retain)
        info.wait_for_publish()  # QoS1: tunggu PUBACK dari broker
        print(f"[pub] [OK] {time.strftime('%H:%M:%S')} {args.topic} -> {args.message} (PUBACK, mid={info.mid})")
        if args.loop <= 0:
            break
        time.sleep(args.loop)

    client.disconnect()
    client.loop_stop()


if __name__ == "__main__":
    main()
