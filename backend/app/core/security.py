import hashlib
import hmac
import secrets
from time import monotonic

from fastapi import Request

from app.core.errors import HubError

COOKIE = "hub_session"


class Security:
    def __init__(self, settings, repository):
        self.settings, self.repository = settings, repository
        self.attempts: dict[str, list[float]] = {}

    def digest(self, token: str):
        return hmac.new(
            self.settings.hub_session_secret.get_secret_value().encode(), token.encode(), hashlib.sha256
        ).hexdigest()

    def origin(self, origin: str | None):
        if origin is not None and origin not in self.settings.hub_allowed_origins:
            raise HubError(403, "FORBIDDEN", "此來源不允許存取平台。")

    def authenticate(self, token: str):
        session = self.repository.session(self.digest(token)) if token else None
        if not session:
            raise HubError(401, "UNAUTHORIZED", "請先登入平台。")
        return session

    def require(self, request: Request, write=False, admin=True):
        session = self.authenticate(request.cookies.get(COOKIE, ""))
        if write:
            self.origin(request.headers.get("origin"))
            if (admin and session["role"] != "admin") or not hmac.compare_digest(
                request.headers.get("x-csrf-token", ""), session["csrf_token"]
            ):
                raise HubError(403, "FORBIDDEN", "操作權限或 CSRF 驗證失敗。")
        return session

    def login(self, username: str, password: str, address: str):
        current = monotonic()
        recent = [stamp for stamp in self.attempts.get(address, []) if current - stamp < 60]
        self.attempts[address] = recent
        if len(recent) >= 10:
            raise HubError(429, "RATE_LIMITED", "登入嘗試過於頻繁，請稍後再試。")
        recent.append(current)
        # 比較固定長度摘要，避免密碼字元編碼及長度影響比較方式。
        expected = (
            self.settings.hub_admin_password.get_secret_value()
            if username == "admin"
            else self.settings.hub_viewer_password.get_secret_value()
            if username == "viewer"
            else ""
        )
        if not expected or not hmac.compare_digest(
            hashlib.sha256(password.encode()).digest(), hashlib.sha256(expected.encode()).digest()
        ):
            raise HubError(401, "UNAUTHORIZED", "帳號或密碼不正確。")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        role = "admin" if username == "admin" else "viewer"
        self.repository.create_session(self.digest(token), csrf, role)
        return token, {"role": role, "csrf_token": csrf, "mode": self.settings.hub_mode}
