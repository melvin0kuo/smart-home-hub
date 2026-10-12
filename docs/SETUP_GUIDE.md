# Home Assistant、設備與平台設定

v0.1.0 先從 [README](../README.md) 啟動 Mock，再按 [HA 安裝指南](HOME_ASSISTANT_LOCAL.md) 建立獨立 Home Assistant。

## 1. 查核網路與型號

從原廠 App／路由器 DHCP 取得 IP，記錄實際型號、硬體與韌體。HA 與設備需可互通；IoT 隔離、AP isolation、VM NAT 與多播會影響探索。不任意關閉整體防火牆、重置或解除配對。

## 2. 逐台加入 HA

| 設備 | 設定與限制 |
| --- | --- |
| P306 | 加入 [TP-Link Smart Home](https://www.home-assistant.io/integrations/tplink/)，用自己的 IP／帳號，依韌體需要啟用 App 第三方相容功能。核對智慧插孔，一般孔不宣告 writable，沒有量測 Entity 不建立功率能力。不要套用 P316M Matter 假設。 |
| C260 | 原廠 App 建立本地攝影機帳號，加入 [ONVIF](https://www.home-assistant.io/integrations/onvif/)，先驗證影像與 PTZ。隱私另需已確認 switch：本平台假設 camera-enabled off = 隱私 on，不可任意映射。瀏覽器不填含密碼 RTSP。 |
| H110 | 需相容整合已產生 remote Entity 與既存按鍵，本平台只送白名單、不學碼。Repo 不含 HA 自訂元件，參考 [研究紀錄](IR_PTZ_SETUP.md)。不是 Xiaomi BLE 網關。 |
| 米家檯燈 | 評估 [HomeKit Device](https://www.home-assistant.io/integrations/homekit_controller/) 或 [Xiaomi Home](https://github.com/XiaoMi/ha_xiaomi_home)。地區依自己的家庭，Apple Home 已有配對不保證能再次配對，不任意重置。 |
| 溫濕度計 | 評估 [Xiaomi BLE](https://www.home-assistant.io/integrations/xiaomi_ble/)，查核標籤、接收器／Proxy、Bindkey、穩定性；本專案尚未完整實測。 |
| 香氛機 | 可選後端 BLE，僅實測 xiaomi.diffuser.xw2iv，見 [藍牙指南](DIFFUSER_BLUETOOTH.md)。一般 Xiaomi BLE 被動接收不是 Mesh 控制。 |
| Electrolux | 先配置相容 HA 社群整合與自己的官方 API 憑證。依 switch／select／number／sensor 映射；EDH14TRBD2 組合限制不能推廣到全部型號。 |

## 3. HA Token

建立平台專用 HA 帳號，再於個人檔案安全性建立長期權杖。只放後端 .env 的 HA_TOKEN，不放 VITE 變數、網址、截圖或日誌。HA Token 不提供完整逐 Entity 隔離，本平台仍使用白名單。

## 4. 私有映射

複製 docs/ha-mapping.example.json 到 .local/ha-mapping.json，從 HA 實體清單取得自己的 Entity ID，替換範例 ID、型號、名稱與房間。設備 ID 保持穩定，target 對應 Entity，同一 Entity 不重複映射。

範本預設 pending／writable=false，先唯讀查核。完成自己的實機測試後，才對該能力設 verification_status=verified、writable=true。路由器與電腦總電源等重要負載可保持唯讀；不可用 mock 冒充實測。

## 5. Real Mode

停止平台，編輯 .env 的 HUB_MODE=real、HA_URL、HA_TOKEN、HUB_MAPPING_FILE，再啟動。HA_URL 不含 /api 或密碼；映射使用絕對路徑。保留平台的隨機密碼與 Session 密鑰。實際格式見 README。

先確認 health、列表與實機一致。命令須取得新狀態才 confirmed；逾時先看設備，不盲目重送。Real 不自動回退 Mock。

## 6. 排除問題

- 找不到 HA：查主機、8123、DNS；使用確認過的 IP。
- 401：查失效／撤銷 Token，不取消驗證或把密碼放 URL。
- 沒按鈕：查已驗證可寫能力、Entity 可用性與資料過期。
- 沒影像：查隱私、本地帳號、HA 串流及網路。
- BLE 離線：查藍牙、距離、手機 App 占用；只跑一個後端 worker。
