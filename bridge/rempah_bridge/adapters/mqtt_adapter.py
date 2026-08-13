"""Paho-MQTT adapter — implements MqttPort."""
import json
import logging

import paho.mqtt.client as mqtt_client

logger = logging.getLogger(__name__)


class PahoMqttAdapter:
    """Thin wrapper around a connected paho Client."""

    def __init__(self, client: mqtt_client.Client) -> None:
        self._client = client

    def publish(self, topic: str, payload: dict) -> None:
        msg = json.dumps(payload)
        info = self._client.publish(topic, msg, qos=1)
        logger.debug("MQTT publish rc=%s topic=%s payload=%s", info.rc, topic, msg)
