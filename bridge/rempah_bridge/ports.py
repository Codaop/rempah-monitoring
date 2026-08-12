from typing import Any, Protocol


class MqttPort(Protocol):
    def publish(self, topic: str, payload: dict) -> None: ...


class DbPort(Protocol):
    def device_state(self, device_id: str) -> Any: ...
