import asyncio
import re
from collections import defaultdict
from time import monotonic

import httpx
from fastapi.responses import Response

from app.core.errors import HubError

ASSET = re.compile(r"(?:master_playlist\.m3u8|playlist\.m3u8|init\.mp4|segment/[0-9]+(?:\.[0-9]+)?\.m4s)")


def rewrite_playlist(text, device_id):
    # 所有播放清單與片段均需平台登入，不公開 HA 串流授權路徑。
    def local(uri):
        name = uri.removeprefix("./")
        if not ASSET.fullmatch(name):
            raise HubError(502, "CAMERA_UNAVAILABLE", "影像播放清單含未支援的資產。")
        return f"/api/cameras/{device_id}/hls/{name}"

    result = []
    for line in text.splitlines():
        if line and not line.startswith("#"):
            line = local(line)
        elif 'URI="' in line:
            line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + local(m[1]) + '"', line)
        result.append(line)
    return "\n".join(result) + "\n"


class CameraGateway:
    def __init__(self):
        self.active = 0
        self.sources = {}
        self.locks = defaultdict(asyncio.Lock)

    async def open(self, request, device_id, asset="master_playlist.m3u8"):
        app = request.app
        app.state.security.require(request)
        if app.state.settings.hub_mode != "real":
            raise HubError(422, "UNSUPPORTED_ACTION", "Mock Mode 沒有真實影像。")
        provider = app.state.provider
        record = next((r for r in provider.records if r.device.id == device_id), None)
        if (
            not record
            or record.device.type != "camera"
            or not any(
                c.name == "camera_stream" and c.readable and c.verification_status == "verified"
                for c in record.device.capabilities
            )
        ):
            raise HubError(404, "CAMERA_NOT_FOUND", "找不到已驗證的攝影機。")
        entity = record.entities.get("main", "")
        if not re.fullmatch(r"camera\.[a-z0-9_]+", entity) or not ASSET.fullmatch(asset):
            raise HubError(404, "CAMERA_NOT_FOUND", "影像資產不存在。")
        directives = list(request.query_params.multi_items())
        params = {}
        for key, value in directives:
            if (
                asset != "playlist.m3u8"
                or key not in {"_HLS_msn", "_HLS_part"}
                or key in params
                or not re.fullmatch(r"[0-9]{1,10}", value)
            ):
                raise HubError(422, "INVALID_PARAMETERS", "串流播放清單參數無效。")
            params[key] = value
        if "_HLS_part" in params and "_HLS_msn" not in params:
            raise HubError(422, "INVALID_PARAMETERS", "串流片段參數缺少序號。")
        device = await app.state.devices.get(device_id)
        if not device.available:
            raise HubError(409, "DEVICE_UNAVAILABLE", "攝影機影像來源目前不可用。")
        if any(c.name == "camera_privacy" for c in device.capabilities) and (
            not device.attributes.get("privacy_available") or device.attributes.get("privacy_enabled")
        ):
            raise HubError(409, "PRIVACY_MODE", "隱私模式已開啟或狀態未確認，無法播放影像。")
        if self.active >= 8:
            raise HubError(429, "STREAM_LIMIT", "影像請求過多，請稍後重試。")
        self.active += 1
        try:
            async with self.locks[device_id]:
                source, expires = self.sources.get(device_id, (None, 0))
                if not source or monotonic() > expires:
                    source = await provider.client.camera_stream(entity)
                    if not isinstance(source, str) or not re.fullmatch(
                        r"/api/hls/[a-zA-Z0-9_-]+/master_playlist\.m3u8", source
                    ):
                        raise HubError(502, "CAMERA_UNAVAILABLE", "HA 回傳的串流路徑無效。")
                    self.sources[device_id] = (source, monotonic() + 120)
            path = source.rsplit("/", 1)[0] + "/" + asset
            async with provider.client.http.stream("GET", path, params=params, timeout=20) as upstream:
                if upstream.status_code != 200:
                    self.sources.pop(device_id, None)
                    raise HubError(502, "CAMERA_UNAVAILABLE", "影像資產讀取失敗。")
                data = bytearray()
                async for chunk in upstream.aiter_bytes():
                    if len(data) + len(chunk) > 8 * 1024 * 1024:
                        raise HubError(502, "CAMERA_UNAVAILABLE", "影像資產超出大小限制。")
                    data.extend(chunk)
            app.state.security.require(request)
            current = await app.state.devices.get(device_id)
            if any(c.name == "camera_privacy" for c in current.capabilities) and (
                not current.attributes.get("privacy_available") or current.attributes.get("privacy_enabled")
            ):
                raise HubError(409, "PRIVACY_MODE", "隱私狀態已變更，停止提供影像。")
            if asset.endswith(".m3u8"):
                text = data.decode("utf8")
                if not text.startswith("#EXTM3U"):
                    raise ValueError()
                return Response(rewrite_playlist(text, device_id), media_type="application/vnd.apple.mpegurl")
            return Response(bytes(data), media_type="video/mp4")
        except (httpx.HTTPError, UnicodeError, ValueError):
            raise HubError(502, "CAMERA_UNAVAILABLE", "攝影機串流連線失敗。") from None
        finally:
            self.active -= 1
