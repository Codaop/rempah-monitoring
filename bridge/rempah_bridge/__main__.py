"""REM-PAH Bridge — entry point (python -m rempah_bridge).

Three background threads run alongside the MQTT loop:
  cmd-poll      polls Supabase for pending commands every COMMAND_POLL_S seconds
  offline-check calls bridge.check_offline() every OFFLINE_CHECK_S seconds
  purge         deletes expired sensor_logs once per PURGE_INTERVAL_S seconds (default: daily)
"""
import json
import logging
import os
from pathlib import Path
import ssl
import threading
import time

import paho.mqtt.client as mqtt_client
from dotenv import load_dotenv
from supabase import create_client

from rempah_bridge.adapters.mqtt_adapter import PahoMqttAdapter
from rempah_bridge.adapters.supabase_adapter import SupabaseDbAdapter
from rempah_bridge.bridge import Bridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rempah.main")

# ── Configuration from environment ───────────────────────────────────────────
# Muat bridge/.env (path eksplisit relatif ke modul, tidak menimpa env yang
# sudah ada, mis. dari Docker -e).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(
            f"Environment variable {name!r} belum diisi. "
            f"Salin bridge/.env.example ke bridge/.env dan isi nilainya, "
            f"atau export {name} di shell sebelum menjalankan bridge."
        )
    return value


MQTT_BROKER          = _require_env("MQTT_BROKER")
MQTT_PORT            = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USERNAME        = _require_env("MQTT_USERNAME")
MQTT_PASSWORD        = _require_env("MQTT_PASSWORD")
SUPABASE_URL         = _require_env("SUPABASE_URL")
SUPABASE_SERVICE_KEY = _require_env("SUPABASE_SERVICE_KEY")
TOPIC_ROOT           = os.environ.get("MQTT_TOPIC_ROOT", "rempah")

OVER_TEMP_THRESHOLD_C = float(os.environ.get("OVER_TEMP_THRESHOLD_C", "100.0"))
OFFLINE_AFTER_S       = float(os.environ.get("OFFLINE_AFTER_S", "60.0"))
DRIP_ML               = float(os.environ.get("DRIP_ML", "0.05"))
YIELD_RATIO_L_PER_KG  = float(os.environ.get("YIELD_RATIO_L_PER_KG", "0.01"))
COMMAND_POLL_S        = float(os.environ.get("COMMAND_POLL_S", "2.0"))
OFFLINE_CHECK_S       = float(os.environ.get("OFFLINE_CHECK_S", "30.0"))
PURGE_INTERVAL_S      = float(os.environ.get("PURGE_INTERVAL_S", str(86400)))

# ── Bridge instance (set after wiring) ───────────────────────────────────────
_bridge: Bridge | None = None


# ── MQTT callbacks ────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, props=None):
    if reason_code == 0:
        logger.info("MQTT connected — subscribing to telemetry and state topics")
        client.subscribe(f"{TOPIC_ROOT}/+/telemetry", qos=1)
        client.subscribe(f"{TOPIC_ROOT}/+/state", qos=1)
    else:
        logger.error("MQTT connection refused: reason_code=%s", reason_code)


def on_disconnect(client, userdata, flags, reason_code, props=None):
    if reason_code != 0:
        logger.warning("MQTT unexpected disconnect: reason_code=%s — paho will reconnect", reason_code)


def on_message(client, userdata, msg):
    bridge = _bridge
    if bridge is None:
        return
    try:
        payload = json.loads(msg.payload)
        parts = msg.topic.split("/")  # rempah/{device_id}/{type}
        if len(parts) != 3:
            return
        _, device_id, msg_type = parts
        if msg_type == "telemetry":
            bridge.handle_telemetry(device_id, payload)
            logger.debug("telemetry device=%s temp=%s", device_id[:8], payload.get("boiler_temp_c"))
        elif msg_type == "state":
            bridge.handle_state(payload)
            logger.info("state device=%s mode=%s cause=%s", device_id[:8], payload.get("mode"), payload.get("cause"))
    except Exception:
        logger.exception("Error handling MQTT message on %s", msg.topic)


# ── Background threads ────────────────────────────────────────────────────────

def _command_poll_loop(bridge: Bridge, db: SupabaseDbAdapter) -> None:
    logger.info("cmd-poll started (%.1fs interval)", COMMAND_POLL_S)
    while True:
        try:
            commands = db.pending_commands()
            for cmd in commands:
                logger.info(
                    "processing command id=%s action=%s device=%s expected=%s",
                    cmd.id[:8], cmd.action, cmd.device_id[:8], cmd.expected_state,
                )
                bridge.process_command(cmd)
        except Exception:
            logger.exception("Command poll error")
        time.sleep(COMMAND_POLL_S)


def _offline_check_loop(bridge: Bridge) -> None:
    logger.info("offline-check started (%.1fs interval)", OFFLINE_CHECK_S)
    while True:
        time.sleep(OFFLINE_CHECK_S)
        try:
            bridge.check_offline()
        except Exception:
            logger.exception("Offline check error")


def _purge_loop(db: SupabaseDbAdapter) -> None:
    logger.info("purge started (%.0fs interval)", PURGE_INTERVAL_S)
    while True:
        time.sleep(PURGE_INTERVAL_S)
        try:
            db.purge_old_sensor_logs()
        except Exception:
            logger.exception("Purge error")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    global _bridge

    # Supabase client (service_role — bypasses RLS)
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    db = SupabaseDbAdapter(
        supabase,
        yield_ratio_l_per_kg=YIELD_RATIO_L_PER_KG,
        drip_ml=DRIP_ML,
    )
    logger.info("Supabase client ready (%s)", SUPABASE_URL)

    # paho-mqtt client
    client = mqtt_client.Client(
        callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
        client_id="rempah-bridge",
        protocol=mqtt_client.MQTTv5,
    )
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set_context(ssl.create_default_context())
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    mqtt_adapter = PahoMqttAdapter(client)

    _bridge = Bridge(
        mqtt=mqtt_adapter,
        db=db,
        over_temp_threshold_c=OVER_TEMP_THRESHOLD_C,
        offline_after_s=OFFLINE_AFTER_S,
        drip_ml=DRIP_ML,
        topic_root=TOPIC_ROOT,
    )

    threading.Thread(target=_command_poll_loop, args=(_bridge, db), daemon=True, name="cmd-poll").start()
    threading.Thread(target=_offline_check_loop, args=(_bridge,), daemon=True, name="offline-check").start()
    threading.Thread(target=_purge_loop, args=(db,), daemon=True, name="purge").start()

    logger.info("Connecting to MQTT broker %s:%d", MQTT_BROKER, MQTT_PORT)
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_forever()  # blocks; paho handles reconnects internally


if __name__ == "__main__":
    main()
