# v0.1.0 設備相容性

實測只適用開發時單台設備／韌體組合，不代表所有區域版本。新使用者需在自己的 HA 查核 Entity 並逐項驗證。

| 設備 | 路徑 | 已測／限制 | 雲端或額外條件 |
| --- | --- | --- | --- |
| P306 | TP-Link Smart Home | 智慧插孔開關實測；一般孔不可控，電力未確認 | 依韌體認證；不預設 Thread／Matter 硬體 |
| H110 | HA remote／社群 IR | 既存按鍵實測；Repo 不含 HA 自訂元件 | App 建檔可能用雲端；不是小米 BLE Gateway |
| C260 | ONVIF／HA Stream／獨立隱私 switch | 影像、PTZ、隱私實測；AI 事件與 Zoom 未測 | 本地帳號，隱私需符合反向語意 |
| 檯燈 1S／yeelink.light.lamp4 | Xiaomi Home；HomeKit 候選 | 開關、亮度、色溫實測，Apple Home 原配對保留 | Xiaomi Home 路徑用雲端；HomeKit 另測 |
| 溫濕度計 3 | Xiaomi BLE 候選 | 標籤、Bindkey、接收與資料待驗證 | 相容 BT／Proxy |
| xiaomi.diffuser.xw2iv，2.1.3_3115 | 後端 BLE Mesh GATT | 開關、2–6 秒、10／15／20 分鐘、1–100% 亮度與 RGB 寫入讀回驗證；定時未接入 | 電腦藍牙及自己的 gatt_ltmk；本次不用小米網關 |
| EDH14TRBD2 | HA Electrolux 社群整合 | 電源、模式、風速、目標濕度、擺風、溫濕度實測；組合限制需查核 | 官方雲端及自己的 API 憑證 |

其他設備未提供可普遍重建的完整硬體／韌體紀錄，因此不宣稱所有版本通用。來源：[TP-Link HA](https://www.home-assistant.io/integrations/tplink/)、[ONVIF](https://www.home-assistant.io/integrations/onvif/)、[Xiaomi Home](https://github.com/XiaoMi/ha_xiaomi_home)、[Xiaomi BLE](https://www.home-assistant.io/integrations/xiaomi_ble/)。

詳細設定見 [SETUP_GUIDE](SETUP_GUIDE.md)。研究文件保留早期歷程，以 README 與此矩陣的第一版狀態為準。
