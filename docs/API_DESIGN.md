# API 與統一設備契約

日期：2026-10-11。以下為本機 MVP 已實作契約；完整 OpenAPI 在 `/docs` 與 `/openapi.json`。JSON 欄位用英文、訊息用繁體中文，時間使用 UTC ISO 8601。

## 授權

`POST /api/auth/login` 使用 `{ "username": "admin", "password": "使用者私有密碼" }`，成功設定 8 小時 HttpOnly Cookie，並回傳 role、csrf_token、mode。可選 viewer 由後端環境變數啟用。`GET /api/auth/me` 取得目前 Session 與 CSRF；`POST /api/auth/logout` 撤銷 Session。除 health／登入／API 文件外，資料 API 均需登入。

所有寫入（含登出）需 `X-CSRF-Token`，控制另需 admin。瀏覽器 Origin 必須在 HUB_ALLOWED_ORIGINS；WebSocket 一定要提供允許的 Origin。不要使用 query string 傳 Token，HA Token 永遠不由前端取得。

## 已實作端點

| 方法 | 路徑 | 行為 |
| --- | --- | --- |
| GET | /api/health | status、mode、integration_connected；HA 斷線為 degraded |
| GET | /api/devices | 標準設備陣列，僅目前模式 |
| GET | /api/devices/{id} | 單一設備；找不到 404 |
| POST | /api/devices/{id}/actions | 受能力／權限／可用性限制的動作，確認後 200 |
| GET | /api/rooms | 由設備資料衍生的房間字串陣列 |
| GET | /api/scenes | Mock 四個示範情境；Real 目前空陣列 |
| POST | /api/scenes/{id}/execute | 先驗證所有步驟，再逐步執行；回傳 confirmed 或 partial_failure |
| GET | /api/history?limit=50 | 操作紀錄，limit 1–200；沒有用電歷史 |
| WS | /ws/events | 受保護即時事件；斷線後客戶端需重連並重新讀取快照 |

## 設備與能力

## 裝置匯入精靈（2026-10-13 新增）

僅管理員可用：`GET /api/integrations/home-assistant/candidates` 回傳 mode、connected、過濾後候選。`POST /api/integrations/home-assistant/test` 接受 entity_id（僅 light／switch）、action（turn_on／turn_off）、confirmed_safe=true，需新的目標狀態才能 confirmed。`POST /api/integrations/home-assistant/import` 接受 `devices` 陣列（1–50），每筆為 entity_id、name、room、protected（預設 true）、enable_control（預設 false）。

所有寫入保留 CSRF；候選由後端重新取得，瀏覽器不能指定能力或任意服務。既有映射禁止覆蓋；控制需十分鐘內雙向證明。錯誤包含 ALREADY_IMPORTED、TEST_NOT_ALLOWED、NO_STATE_CHANGE、VERIFICATION_REQUIRED、IMPORT_STORAGE_ERROR。詳見 [匯入指南](DEVICE_IMPORT.md)。

## 設備欄位

欄位：id、name、manufacturer、model、type、room、online、available、state、capabilities、attributes、source、last_updated，另加 verification_status、state_confidence、stale。source 僅 mock／home_assistant。

capability 包含 name、target（預設 main）、readable、writable、verification_status（mock／verified／pending／unsupported）、minimum、maximum、unit。只有 writable 且 mock／verified、設備 available 且非 stale 的能力才可操作；Real 映射不得使用 mock。

一個延長線可對應多個 Entity，P306 以 outlet-1…outlet-3 識別智慧 AC；一般 AC 不可寫，功率能力未確認。不得直接接受前端指定 entity_id／domain／service。Sensor 與攝影機回應不包含原始 HA attributes。

## 動作

```json
{"action":"turn_off","target":"outlet-1","parameters":{}}
```

允許 turn_on／turn_off／set_brightness／set_color_temperature。開關不可攜帶參數；亮度與色溫需數值 parameters.value，範圍依能力定義。額外欄位、布林充當數值及非法命令會拒絕。

成功：`{"operation_id":"…","status":"confirmed","device":{…},"source":"mock"}`。Mock confirmed 只表示模擬結果。Real 在 REST service 接受後等待新的 HA 目標狀態確認，逾時不會假裝成功。

情境不是交易，部分失敗不反向切換已完成的電器。回應 results 列出每步結果；尚無自訂情境寫入 API。

## 錯誤

統一格式：`{"error":{"code":"UNSUPPORTED_ACTION","message":"…","request_id":"…"}}`。

| HTTP | 意義 |
| --- | --- |
| 401 / 403 / 429 | 未登入／權限、CSRF 或來源不符／登入過頻 |
| 404 / 409 / 422 | 找不到／離線或不可用／不支援能力或參數錯誤 |
| 502 / 503 / 504 | HA 授權或格式錯誤／無法連線／等待逾時 |
| 500 | 未預期錯誤，對外不回傳原始例外 |

逾時可能代表電器已執行但無法確認；先查設備實際狀態再決定操作。

## 事件

provider.status（connected）、device.updated（device）、operation.updated（operation）、resync_required。一般事件含 sequence、mode、occurred_at；最初 provider.status 為連線快照，無 sequence。不要依賴跨服務重新啟動的序號連續性。瀏覽器重新連線或 resync 時重新呼叫 GET /api/devices 與 history。Session 過期／登出會中止 WS。

參考：[HA REST](https://developers.home-assistant.io/docs/api/rest/)、[HA WebSocket](https://developers.home-assistant.io/docs/api/websocket/)。


## 2026-10-12 自製頁面控制與負載標示

啟用私有 `.local/ha-mapping.active.json`，只有已實測 P306 插孔 1 的 switch 能力 writable=true；插孔 2、3 保持 false。頁面逐孔顯示已開啟／已關閉與負載、鎖定原因，移除 P306 卡片上容易被誤認為總開關的重複控制。後端 Capability 新增可選 label／control_note，Device 新增 integration_note，皆取自私有白名單，不轉送 HA 原始屬性。舊映射可繼續使用。

H110 顯示網關狀態與 IR 待支援，C260 明確區分自製串流未接入與 HA 實體可用性。Real Mode 最近操作空白提示不再要求操作模擬插孔。

驗證：後端 pytest 25 項通過、Ruff 通過；前端 Vitest 3 項通過，包含裝置卡片僅一個開關、重要負載鎖定與離線不提供操作；ESLint、TypeScript／Vite build 通過。私人 HTTPS 瀏覽器確認新頁面、負載標籤與唯一插孔 1 開關。實際 API 驗證兩個鎖定孔回傳 UNSUPPORTED_ACTION；此次沒有切換任何實體電源，不將 UI 變更當作新增實機測試。


## 2026-10-12 C260 影像、隱私模式與紅外線頁面

C260 原生 TP-Link API 曾回傳 INTERNAL_QUERY_ERROR，導致全部原生實體 unavailable；僅重載該整合未立即修復，後續原生 switch 自行恢復 on。沒有重設設備、韌體、帳密或配對。使用既有 HA 攝影機專用憑證建立獨立 Generic Camera，RTSP `/stream2` 驗證成功。平台仍只有一張 C260 卡片，main 映射 Generic Camera；原生 switch 僅用於 privacy 子能力。

Generic Camera 沒有 still_image_url 時，MJPEG 回應無影像幀，故最終採 HA Stream HLS。後端用 HA WebSocket camera/stream 取得私有端點，重新寫入播放清單 URI；每個 m3u8／init.mp4／m4s 都須平台登入，禁止任意 URL、路徑跳脫與未映射攝影機，HA Token、RTSP 與 HA 串流授權路徑均不送往瀏覽器。片段限制 8 MiB，同時最多 8 個資產請求，逾時 20 秒。登出後不能再下載；瀏覽器先前已緩衝的內容無法遠端撤回。

私人 HTTPS 實測 HLS master、播放清單、init MP4 及真實 m4s 都成功，瀏覽器影片 1280×720、paused=false、無 MediaError、currentTime 增加。先使用相容子串流，音訊依來源支援且預設靜音；PTZ 尚未開放。內建瀏覽器原生 HLS 路徑失敗，改優先 Hls.js 後播放成功；不支援 MSE 時才使用原生 HLS。手機端仍待實測，播放可能延遲數秒。

隱私模式：已查核本機 python-kasa Camera.set_state，HA switch.tapo_c260 的 on 代表 privacy=false，off 代表 privacy=true。新增 enable_privacy／disable_privacy，僅允許已映射 privacy target，以 switch.turn_off／turn_on 反向轉換，收到新的目標狀態才顯示確認。隱私未知或開啟時後端拒絕播放；狀態變更時前端卸載播放器，關閉隱私後仍須手動播放。此次只讀取實際 privacy=false，沒有切換實機隱私模式；反向控制與確認流程由測試驗證，仍待使用者實機操作確認。

紅外線頁面列出實際發現的機上盒、Dyson 風扇、HERAN 冷氣、TECO 電視遙控器。現有 H110／python-kasa 沒有可用 IR 控制 Entity，四個設備 commands=[]、verified=false，不提供假遙控按鈕。後端保留已驗證 HA remote.send_command 白名單介面，前端只能送 command id，不能指定任意 Entity、原始碼或 service；需要管理員與 CSRF，記錄 sent／inferred，不假稱電器狀態確認。此擴充介面僅測試替身驗證，H110 實際控制尚未完成。

驗證涵蓋登入、資產白名單、外部 URI／路徑跳脫、上游錯誤、離線、併發上限、登出阻擋、隱私阻擋及反向語意、IR 非法指令。Vite build 成功但播放器套件使主 bundle 超過 500 kB，後續可延遲載入優化。

來源：[HA Generic Camera](https://www.home-assistant.io/integrations/generic/)、[HA Camera](https://www.home-assistant.io/integrations/camera/)、[HA TP-Link](https://www.home-assistant.io/integrations/tplink/)、[Hls.js](https://github.com/video-dev/hls.js)、[TP-Link H110 討論（歷史資訊，不視為最新韌體實測）](https://community.tp-link.com/en/home/forum/topic/829318)。

## C260 PTZ 與 H110 紅外線更新（2026-10-12）

`POST /api/cameras/{id}/ptz` 接受 `{"direction":"left"}`，direction 僅允許 left／right／up／down／stop，拒絕額外參數。需要管理員 Session、CSRF 與已驗證的 camera_ptz 映射。移動前檢查最新隱私／ONVIF 狀態；每次固定 1 秒並補送停止，不自動重試移動。成功回應 sent，不假造角度確認。C260 隱私開啟時拒絕 ONVIF Stop，頁面停用 PTZ；停止 API 仍允許授權管理員嘗試，失敗會回傳統一錯誤。

紅外線端點沿用既有白名單；目前三組遙控器共 43 個實機清單按鍵。傳送介面經實測，但電器端逐鍵效果仍待現場確認。詳見 IR_PTZ_SETUP.md。


### 除濕機操作

既有 `POST /api/devices/{id}/actions` 新增：

- `set_mode`，target `mode`，parameters `{"value":"Complete"}`，只能使用映射的選項。
- `set_operative_mode`，target `operative_mode`，parameters `{"value":"Manual"}`。
- `set_target_humidity`，target `humidity_target`，parameters `{"value":55}`；35–85%，間距5%。設備須開機且為 Complete／Manual，否則回傳409 MODE_CONFLICT。

電源沿用 turn_on／turn_off。所有操作仍需管理員驗證、CSRF、防止離線操作及新狀態回報確認；同設備的不同控制循序執行，避免模式與濕度命令競爭。沒有已驗證能力的設備回傳422。

- `set_fan_speed`，target `fan_speed`，parameters `{"value":"Middle"}`；僅 Low／Middle／High，設備開機且手動模式時允許。Auto 不是可寫入的風速選項。
## 本機藍牙香氛機（2026-10-13）

`Device.source` 新增 `bluetooth`。沿用既有登入、CSRF、角色限制及 `/api/devices/{id}/actions`；沒有新增未授權 BLE 入口。開關使用 `turn_on`／`turn_off`，`target=main` 表示擴香、`target=light` 表示氛圍燈。

數值動作均為 `parameters: {"value": 整數}`：`set_diffusion_duration`（main，2–6，步進 1）、`set_diffusion_interval`（main，10–20，步進 5）、`set_brightness`（light，1–100）、`set_color`（light，0–16777215）。只向具有已驗證能力的設備開放；HA 既有燈具仍使用原本 brightness 語意。

設定只有在應用層回覆成功且讀回目標值後才回傳 `confirmed`。藍牙離線回傳 409，確認失敗回傳 504；不自動重送可能已執行的命令。詳見 [藍牙整合文件](DIFFUSER_BLUETOOTH.md)。
