from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import HubError
from app.services.imports import ImportItem
from app.services.onboarding import OnboardingService

router = APIRouter(prefix="/api/integrations/home-assistant", tags=["裝置匯入"])


def admin(request: Request):
    session = request.app.state.security.require(request, write=request.method != "GET")
    if session["role"] != "admin":
        raise HubError(403, "FORBIDDEN", "只有管理員可以匯入設備。")


class TestSwitch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str = Field(pattern=r"^(light|switch)\.[a-z0-9_]+$", max_length=255)
    action: Literal["turn_on", "turn_off"]
    confirmed_safe: Literal[True]


class ImportDevices(BaseModel):
    model_config = ConfigDict(extra="forbid")
    devices: list[ImportItem] = Field(min_length=1, max_length=50)


@router.get("/onboarding", dependencies=[Depends(admin)])
async def onboarding(request: Request):
    settings = request.app.state.settings
    ha = getattr(request.app.state.provider, "client", None)
    return await OnboardingService(ha, settings.hub_mode, settings.ha_browser_url or settings.ha_url).load()


@router.get("/candidates", dependencies=[Depends(admin)])
async def candidates(request: Request):
    return await request.app.state.imports.discover()


@router.post("/test", dependencies=[Depends(admin)])
async def test_switch(body: TestSwitch, request: Request):
    return await request.app.state.imports.test_switch(body.entity_id, body.action)


@router.post("/import", dependencies=[Depends(admin)])
async def import_devices(body: ImportDevices, request: Request):
    devices = await request.app.state.imports.import_devices(body.devices)
    return {"status": "imported", "devices": devices, "mode": request.app.state.settings.hub_mode}
