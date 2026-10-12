from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Capability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    target: str = "main"
    readable: bool = True
    writable: bool = False
    verification_status: Literal["mock", "verified", "pending", "unsupported"] = "pending"
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = Field(default=None, gt=0)
    options: list[str] = Field(default_factory=list)
    unit: str | None = None
    label: str | None = Field(default=None, max_length=120)
    control_note: str | None = Field(default=None, max_length=240)


class Device(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    manufacturer: str
    model: str
    type: str
    room: str
    online: bool | None = None
    available: bool = False
    state: str = "unknown"
    capabilities: list[Capability] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    source: Literal["mock", "home_assistant", "bluetooth"]
    verification_status: str = "pending"
    state_confidence: str = "unknown"
    stale: bool = False
    last_updated: str | None = None
    integration_note: str | None = Field(default=None, max_length=500)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "turn_on",
        "turn_off",
        "set_brightness",
        "set_color_temperature",
        "enable_privacy",
        "disable_privacy",
        "set_target_humidity",
        "set_mode",
        "set_operative_mode",
        "set_fan_speed",
        "set_diffusion_duration",
        "set_diffusion_interval",
        "set_color",
    ]
    target: str = Field(default="main", max_length=64)
    parameters: dict[str, StrictInt | StrictFloat | StrictStr] = Field(default_factory=dict)
