import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.api.imports import router as imports_router
from app.api.media import router as media_router
from app.api.routes import router
from app.core.config import ROOT, Settings
from app.core.errors import HubError, error_response, hub_error_handler
from app.core.security import Security
from app.integrations.mock import MockProvider
from app.services.camera import CameraGateway
from app.services.devices import DeviceService
from app.services.events import EventBus
from app.services.imports import ImportService
from app.services.repository import Repository
from app.services.sensor_history import SensorHistory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        repository = Repository(settings.hub_database_url, settings.hub_mode)
        bus = EventBus(settings.hub_mode)
        if settings.hub_mode == "mock":
            provider = MockProvider()
            for record in repository.restore():
                if record["id"] in provider.items:
                    # 僅恢復模擬設備的可控制狀態，不讓磁碟內容增加能力。
                    item = provider.items[record["id"]]
                    if item.type in {"light", "power_strip"}:
                        item.state, item.attributes = record["state"], record["attributes"]
        else:
            from app.integrations.real import RealProvider

            provider = RealProvider(settings, bus)
        app.state.settings, app.state.provider = settings, provider
        app.state.repository, app.state.bus = repository, bus
        app.state.security = Security(settings, repository)
        app.state.cameras = CameraGateway()
        app.state.devices = DeviceService(provider, repository, bus)
        app.state.imports = ImportService(provider, repository, bus, settings.hub_mode)
        app.state.sensor_history = SensorHistory(provider, repository)
        history_task = asyncio.create_task(app.state.sensor_history.run())
        task = asyncio.create_task(provider.run()) if settings.hub_mode == "real" else None
        try:
            yield
        finally:
            history_task.cancel()
            await asyncio.gather(history_task, return_exceptions=True)
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await provider.close()
            repository.engine.dispose()

    app = FastAPI(title="Smart Home Hub 智慧家庭 API", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    app.include_router(media_router)
    app.include_router(imports_router)
    if settings.hub_serve_frontend:
        # 只公開前端建置目錄，不允許將專案根目錄或秘密檔掛載為靜態內容。
        static = ROOT / "frontend" / "dist"
        if not (static / "index.html").is_file():
            raise ValueError("請先執行前端 npm run build，再啟用 HUB_SERVE_FRONTEND")
        app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    app.add_exception_handler(HubError, hub_error_handler)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, error: RequestValidationError):
        return error_response(422, "INVALID_PARAMETERS", "請求格式或參數不正確。")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception):
        return error_response(500, "INTERNAL_ERROR", "服務發生錯誤，請使用關聯 ID 查詢。")

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app
