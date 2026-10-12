"""沿用 HA 當前版本的整合目錄；不代理登入或變更配對。"""

import asyncio
import ipaddress
import re
from urllib.parse import urlsplit

DOMAIN = re.compile(r"^[a-z][a-z0-9_]{0,99}$")

# 指引只補充常見流程；可加入的整合仍以 HA 回覆為準。
GUIDES = {
    "matter": (
        "Matter",
        "協定",
        "Matter 配對碼；Thread 設備另需可用的 Thread 邊界路由器。",
        "在 HA 的 Matter 設定中加入設備；手機配對可能需要 HA Companion App。",
        "Matter Wi-Fi Thread",
    ),
    "zha": (
        "Zigbee",
        "協定",
        "相容的 Zigbee 協調器，樹莓派內建藍牙不能代替。",
        "先設定 ZHA 協調器，再於 ZHA 加入設備並讓設備進入配對模式。",
        "Zigbee ZHA Aqara IKEA",
    ),
    "mqtt": (
        "MQTT／Zigbee2MQTT",
        "協定",
        "MQTT Broker；Zigbee2MQTT 另需 Zigbee 協調器與服務。",
        "設定 MQTT 連線並啟用設備的 Discovery；Zigbee 設備於 Zigbee2MQTT 配對。",
        "MQTT Zigbee2MQTT Tasmota",
    ),
    "bluetooth": (
        "Bluetooth 藍牙",
        "協定",
        "HA 主機可存取的藍牙介面或相容 ESPHome Bluetooth Proxy。",
        "確認 HA 能接收藍牙訊號；再選設備對應品牌整合。藍牙本身不提供所有品牌的控制指令。",
        "BLE 藍牙 Bluetooth",
    ),
    "onvif": (
        "ONVIF 網路攝影機",
        "協定",
        "支援 ONVIF 的攝影機及攝影機專用帳號。",
        "在攝影機開啟 ONVIF，於 HA 填入位址及專用帳號；PTZ 與事件依型號驗證。",
        "攝影機 camera RTSP ONVIF",
    ),
    "homekit_controller": (
        "HomeKit Device",
        "協定",
        "支援 HomeKit 的設備與配對碼。",
        "設備需能供 HA 配對；已加入 Apple 家庭時不可直接重複配對，請先評估現有設定。",
        "Apple HomeKit 家庭",
    ),
    "esphome": (
        "ESPHome",
        "協定",
        "已運行 ESPHome 的設備；加密 API 可能需要金鑰。",
        "選取探索到的 ESPHome 設備，或填入位址與 API 金鑰；不會自動刷韌體。",
        "ESP32 ESP8266 ESPHome",
    ),
    "zwave_js": (
        "Z-Wave",
        "協定",
        "與所在地頻段相符的 Z-Wave 控制器及 Z-Wave JS 服務。",
        "先設定控制器，再進行設備加入流程。",
        "Z-Wave ZWave",
    ),
    "tplink": (
        "TP-Link Smart Home",
        "品牌",
        "同網路可互通的相容 Tapo／Kasa 設備；依型號需要帳號或第三方相容設定。",
        "在 HA 的 TP-Link Smart Home 完成探索或登入；功能依實際型號、韌體及實體確認。",
        "TP-Link Tapo Kasa 插座",
    ),
    "xiaomi_home": (
        "Xiaomi Home 米家",
        "品牌",
        "已安裝 Xiaomi Home 社群整合及相同地區的小米帳號。",
        "於 HA 完成官方登入與家庭選擇；BLE 設備可能另需可用網關，不能假設雲端登入即可控制。",
        "Xiaomi 小米 米家",
    ),
}


def browser_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or any(c.isspace() for c in value)
        or "\\" in value
    ):
        raise ValueError("HA_BROWSER_URL 必須是無帳密、查詢參數及片段的 HTTP(S) 網址")
    try:
        parsed.port
    except ValueError:
        raise ValueError("HA_BROWSER_URL 連接埠不正確") from None
    return value.rstrip("/")


def metadata_index(descriptions):
    index, aliases = {}, {}
    if not isinstance(descriptions, dict):
        return index, aliases
    for source in ("core", "custom"):
        group = descriptions.get(source, {})
        entries = group.get("integration", {}) if isinstance(group, dict) else {}
        if not isinstance(entries, dict):
            continue
        for domain, row in entries.items():
            if not isinstance(row, dict):
                continue
            nested = row.get("integrations")
            rows = nested if isinstance(nested, dict) else {domain: row}
            for key, item in rows.items():
                if not isinstance(key, str) or not DOMAIN.fullmatch(key) or not isinstance(item, dict):
                    continue
                index[key] = {**item, "custom": source == "custom"}
                target = item.get("supported_by")
                if isinstance(target, str) and DOMAIN.fullmatch(target):
                    name = item.get("name")
                    if isinstance(name, str):
                        aliases.setdefault(target, []).append(name[:150])
    return index, aliases


class OnboardingService:
    def __init__(self, ha, mode, url):
        self.ha, self.mode = ha, mode
        self.url = browser_url(url) if url else ""

    async def load(self):
        errors = []
        if self.mode == "mock":
            handlers, descriptions, flows = list(GUIDES), {}, []
            catalog_status = discovery_status = "demo"
        else:
            handlers, descriptions, flows = await asyncio.gather(
                self.ha.request("GET", "api/config/config_entries/flow_handlers"),
                self.ha.onboarding_read("integration/descriptions"),
                self.ha.onboarding_read("config_entries/flow/progress"),
                return_exceptions=True,
            )
            valid_handlers = isinstance(handlers, list) and all(isinstance(x, str) for x in handlers)
            catalog_status = "available" if valid_handlers else "unavailable"
            if not valid_handlers:
                handlers = []
                errors.append("無法讀取可設定整合；目前只顯示參考指引，請確認 HA 連線與管理員權限。")
            if not isinstance(descriptions, dict):
                descriptions = {}
                errors.append("品牌名稱資料暫時無法取得，部分項目顯示整合代碼。")
            discovery_status = "available" if isinstance(flows, list) else "unavailable"
            if not isinstance(flows, list):
                flows = []
                errors.append("無法讀取探索結果；仍可搜尋品牌手動加入。")
        index, aliases = metadata_index(descriptions)
        available = {d for d in handlers if DOMAIN.fullmatch(d)}
        catalog = []
        for domain in sorted(available | set(GUIDES)):
            meta = index.get(domain, {})
            if meta.get("integration_type") in ("helper", "system", "entity", "virtual"):
                continue
            guide = GUIDES.get(domain)
            name = guide[0] if guide else meta.get("name", domain)
            name = name[:150] if isinstance(name, str) else domain
            ready = domain in available
            documentation = (
                "https://github.com/XiaoMi/ha_xiaomi_home"
                if domain == "xiaomi_home"
                else None
                if meta.get("custom")
                else f"https://www.home-assistant.io/integrations/{domain}/"
            )
            catalog.append(
                {
                    "domain": domain,
                    "name": name,
                    "category": guide[1] if guide else "整合",
                    "keywords": " ".join([domain, name, *aliases.get(domain, []), guide[4] if guide else ""]),
                    "available": ready,
                    "requirements": guide[2] if guide else "依官方整合文件確認型號、網路條件與必要帳號。",
                    "instructions": guide[3]
                    if guide
                    else "在 HA 完成設定或登入，再回來讀取設備。社群文件請於 HA 整合詳細資料查看。"
                    if meta.get("custom")
                    else "在 HA 完成此整合的設定或登入，再返回平台讀取設備。",
                    "documentation_url": documentation,
                    "setup_url": f"{self.url}/config/integrations/dashboard/add?domain={domain}"
                    if ready and self.url and self.mode == "real"
                    else None,
                }
            )
        lookup = {row["domain"]: row for row in catalog}
        discovered = []
        for flow in flows:
            if not isinstance(flow, dict):
                continue
            domain, context = flow.get("handler"), flow.get("context", {})
            source = context.get("source") if isinstance(context, dict) else None
            if (
                not isinstance(domain, str)
                or not DOMAIN.fullmatch(domain)
                or not isinstance(source, str)
                or source
                not in {
                    "zeroconf",
                    "ssdp",
                    "dhcp",
                    "bluetooth",
                    "usb",
                    "homekit",
                    "mqtt",
                    "discovery",
                    "integration_discovery",
                    "esphome",
                    "hardware",
                    "hassio",
                    "unignore",
                }
            ):
                continue
            # 不輸出 context / title_placeholders，可能含網址、帳號或機密。
            discovered.append(
                {
                    "id": len(discovered) + 1,
                    "domain": domain,
                    "name": lookup.get(domain, {}).get("name", domain),
                    "source": source,
                    "setup_url": f"{self.url}/config/integrations/dashboard"
                    if self.url and self.mode == "real"
                    else None,
                }
            )
        hostname = urlsplit(self.url).hostname or ""
        try:
            local_only = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            local_only = hostname.lower() == "localhost"
        return {
            "mode": self.mode,
            "catalog_status": catalog_status,
            "discovery_status": discovery_status,
            "catalog": catalog,
            "discovered": discovered,
            "warnings": errors,
            "local_only_url": local_only,
        }
