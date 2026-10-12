from typing import Protocol

from app.models.device import Action, Device


class DeviceProvider(Protocol):
    connected: bool

    async def devices(self) -> list[Device]: ...
    async def action(self, device_id: str, action: Action) -> Device: ...
