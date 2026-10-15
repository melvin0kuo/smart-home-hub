"""HA OS App 啟動設定；不輸出秘密、不存取 Supervisor 管理 API。"""

import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit


def private_write(path: Path, text: str):
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(text)
    temporary.replace(path)
    path.chmod(0o600)


def prepare(options: dict, data: Path) -> dict:
    data.mkdir(parents=True, exist_ok=True)
    origins = options.get("allowed_origins", [])
    if not isinstance(origins, list) or not origins:
        raise ValueError("至少設定一個允許來源")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or any(c.isspace() for c in origin)
        ):
            raise ValueError("允許來源必須是 HTTP(S) origin，不含帳密或路徑")
    mapping = options.get("mapping_json", "").strip()
    if mapping:
        from app.integrations.real import MappingFile

        try:
            parsed_mapping = MappingFile.model_validate_json(mapping)
        except ValueError:
            raise ValueError("私有映射格式不正確，請使用平台範例格式") from None
        mapping = parsed_mapping.model_dump_json()
    session_path = data / "session-secret"
    if not session_path.exists():
        private_write(session_path, secrets.token_urlsafe(48))
    mapping_path = data / "device-mapping.json"
    if mapping:
        private_write(mapping_path, mapping)
    return {
        "hub_mode": options.get("mode", "mock"),
        "hub_admin_password": options.get("admin_password", ""),
        "hub_session_secret": session_path.read_text(encoding="utf-8").strip(),
        "hub_database_url": f"sqlite:///{data / 'hub.db'}",
        "hub_serve_frontend": True,
        "hub_allowed_origins": [origin.rstrip("/") for origin in origins],
        "hub_mapping_file": str(mapping_path) if mapping else "",
        "ha_url": options.get("ha_url", ""),
        "ha_browser_url": options.get("ha_browser_url", ""),
        "ha_token": options.get("ha_token", ""),
    }


def main():
    sys.path.insert(0, "/app/backend")
    import uvicorn
    from app.core.config import Settings
    from app.main import create_app

    try:
        options = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))
        settings = Settings(_env_file=None, **prepare(options, Path("/data")))
    except (OSError, ValueError, TypeError):
        # 驗證例外可能包含原始秘密欄位，不能將例外直接輸出到 App 日誌。
        print(
            "App 設定無效：請檢查管理員密碼長度、HA 連線、允許來源及私有映射。",
            flush=True,
        )
        raise SystemExit(1) from None
    uvicorn.run(create_app(settings), host="0.0.0.0", port=8000, workers=1)


if __name__ == "__main__":
    main()
