from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    hub_mode: Literal["mock", "real"] = "mock"
    hub_admin_password: SecretStr
    hub_session_secret: SecretStr
    hub_viewer_password: SecretStr = SecretStr("")
    hub_database_url: str = "sqlite:///./data/hub.db"
    hub_secure_cookie: bool = False
    hub_serve_frontend: bool = False
    hub_mapping_file: str = ""
    hub_ble_diffuser_config: str = ""
    hub_allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    ha_url: str = ""
    ha_browser_url: str = ""
    ha_token: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def validate_secrets(self):
        if self.ha_browser_url:
            from app.services.onboarding import browser_url

            browser_url(self.ha_browser_url)
        if len(self.hub_admin_password.get_secret_value()) < 12:
            raise ValueError("平台密碼至少需要 12 個字元")
        if len(self.hub_session_secret.get_secret_value()) < 32:
            raise ValueError("Session 密鑰至少需要 32 個字元")
        if not self.hub_database_url.startswith("sqlite:///"):
            raise ValueError("本版僅支援 SQLite")
        if self.hub_mode == "real":
            parsed = urlparse(self.ha_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or not self.ha_token.get_secret_value()
            ):
                raise ValueError("Real Mode 需要合法 HA URL 與 Token")
        return self
