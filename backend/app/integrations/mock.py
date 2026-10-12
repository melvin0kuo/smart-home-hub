from app.models.device import Action, Capability, Device, now


def capability(name, target="main", writable=False, minimum=None, maximum=None, unit=None):
    return Capability(
        name=name,
        target=target,
        writable=writable,
        verification_status="mock",
        minimum=minimum,
        maximum=maximum,
        unit=unit,
    )


class MockProvider:
    connected = True

    def __init__(self):
        common = dict(
            source="mock", verification_status="mock", state_confidence="simulated", last_updated=now()
        )
        devices = [
            Device(
                id="mock-p306",
                name="書房智慧擴充插座",
                manufacturer="TP-Link",
                model="P306",
                type="power_strip",
                room="書房",
                online=True,
                available=True,
                state="mixed",
                capabilities=[capability("switch", f"outlet-{i}", True) for i in range(1, 4)],
                attributes={
                    "outlets": [
                        {
                            "id": f"outlet-{i}",
                            "name": f"插孔 {i}" if i <= 3 else f"一般插座 {i - 3}",
                            "state": "on" if i <= 3 else "always_on",
                        }
                        for i in range(1, 7)
                    ],
                    "note": (
                        "3 個智慧 AC 開關為模擬；3 個一般 AC 不可遙控。"
                        "USB 群組與夜燈整合待驗證，未提供用電資料。"
                    ),
                },
                **common,
            ),
            Device(
                id="mock-lamp",
                name="工作桌檯燈",
                manufacturer="Xiaomi",
                model="米家檯燈 1S",
                type="light",
                room="書房",
                online=True,
                available=True,
                state="on",
                capabilities=[
                    capability("switch", writable=True),
                    capability("brightness", writable=True, minimum=0, maximum=100, unit="%"),
                    capability("color_temperature", writable=True, minimum=2600, maximum=5000, unit="K"),
                ],
                attributes={
                    "brightness": 70,
                    "color_temperature": 4000,
                    "note": "此調光範圍僅供模擬；實機需依 Entity 驗證。",
                },
                **common,
            ),
            Device(
                id="mock-thermometer",
                name="客廳溫濕度計",
                manufacturer="Xiaomi",
                model="MJWSD05MMC",
                type="sensor",
                room="客廳",
                online=True,
                available=True,
                state="measuring",
                capabilities=[
                    capability("temperature_sensor", unit="°C"),
                    capability("humidity_sensor", unit="%"),
                    capability("battery_sensor", unit="%"),
                ],
                attributes={
                    "temperature": 25.6,
                    "humidity": 58,
                    "battery": 87,
                    "note": "靜態模擬感測值；原廠 BLE 整合與 Bindkey 待驗證。",
                },
                **common,
            ),
            Device(
                id="mock-camera",
                name="客廳攝影機",
                manufacturer="TP-Link",
                model="C260",
                type="camera",
                room="客廳",
                online=False,
                available=False,
                state="unavailable",
                attributes={"note": "尚未連接影像。ONVIF、RTSP、PTZ 與事件均待實測。"},
                **common,
            ),
            Device(
                id="mock-h110",
                name="客廳紅外線網關",
                manufacturer="TP-Link",
                model="H110",
                type="gateway",
                room="客廳",
                online=True,
                available=True,
                state="pending",
                attributes={"note": "連線狀態為模擬；Matter 子設備與 IR 能力待實測。"},
                **common,
            ),
            Device(
                id="mock-diffuser",
                name="臥室智慧香氛機",
                manufacturer="Xiaomi",
                model="MJXFJ03XW",
                type="diffuser",
                room="臥室",
                online=None,
                available=False,
                state="unsupported",
                attributes={"note": "暫不支援控制。保留設備紀錄，尚無可靠的型號整合。"},
                **common,
            ),
        ]
        self.items = {device.id: device for device in devices}

    async def devices(self):
        return [device.model_copy(deep=True) for device in self.items.values()]

    async def action(self, device_id: str, action: Action):
        device = self.items[device_id]
        if action.action in {"turn_on", "turn_off"}:
            state = "on" if action.action == "turn_on" else "off"
            if device.type == "power_strip":
                next(outlet for outlet in device.attributes["outlets"] if outlet["id"] == action.target)[
                    "state"
                ] = state
                states = {
                    outlet["state"]
                    for outlet in device.attributes["outlets"]
                    if outlet["id"] in {"outlet-1", "outlet-2", "outlet-3"}
                }
                device.state = states.pop() if len(states) == 1 else "mixed"

            else:
                device.state = state
        else:
            key = "brightness" if action.action == "set_brightness" else "color_temperature"
            device.attributes[key] = action.parameters["value"]
        device.last_updated = now()
        return device.model_copy(deep=True)
