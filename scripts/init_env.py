from pathlib import Path
import secrets
root = Path(__file__).resolve().parents[1]
target = root / ".env"
if not target.exists():
    content = (root / ".env.example").read_text(encoding="utf8")
    content = content.replace("HUB_ADMIN_PASSWORD=", "HUB_ADMIN_PASSWORD=" + secrets.token_urlsafe(18), 1)
    content = content.replace("HUB_SESSION_SECRET=", "HUB_SESSION_SECRET=" + secrets.token_urlsafe(48), 1)
    target.write_text(content, encoding="utf8")
    target.chmod(0o600)
    print("已建立本機 .env；密碼與秘密不會輸出到日誌。")
else:
    print("保留既有 .env。")
