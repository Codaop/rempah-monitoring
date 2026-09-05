from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeviceState:
    device_id: str
    mode: str


@dataclass(frozen=True)
class Command:
    id: str
    device_id: str
    action: str
    expected_state: Optional[str] = None
    payload: Optional[dict] = None
