# 本機測試與驗證紀錄

日期：2026-10-11（Asia/Taipei）。範圍為 Windows 本機 Mock MVP 與模擬 HA 服務，**沒有實體設備成功紀錄**。

| 項目 | 結果 | 證據與涵蓋範圍 |
| --- | --- | --- |
| pytest | 22 passed | API／六種設備／逐孔控制／離線／非法能力與參數／CSRF／未授權／viewer／WS、HA REST 錯誤與逾時、WS 快照事件重連、Real 狀態確認及異常資料隔離 |
| Ruff | 通過 | backend/app、backend/tests；Python 程式已格式化 |
| Vitest | 2 passed | 前端 target 對應能力、離線／過期／未驗證拒絕控制 |
| ESLint | 通過 | 前端與瀏覽器測試來源 |
| TypeScript + Vite build | 通過 | 正式靜態資產成功產生，未代表正式部署已驗證 |
| npm audit | 0 vulnerabilities | 本次鎖定套件樹，查詢時間僅代表此輪結果 |
| Playwright / Edge | 1 passed | 真正瀏覽器登入、六設備、單孔控制、待支援無按鈕、工作情境、亮度、深淺色切換、390px 無水平溢位、手機登出 |
| 啟動／停止／重啟 | 通過 | 隱藏背景程序；修正 PowerShell JSON 日期自動解析造成的程序辨識問題；只停止 ID 與啟動時間都相符的本專案程序 |
| health／API 文件 | 通過 | localhost:8000/api/health 為 mock、ok；/docs HTTP 200 |
| Git 忽略與文件連結 | 通過 | .env、.venv、資料庫、node_modules、.local 均被忽略；本地 Markdown 連結無缺檔 |
| 程式碼審查 | 修正後通過本輪範圍 | 獨立唯讀審查無 Critical；四項 Important 修正並複核，詳見下方 |

## 審查修正

1. Real 不可用操作前的快取確認本次命令；需新的 Entity revision，亮度／色溫也需電源狀態 on。
2. HA WebSocket 穩態不設 30 秒應用訊息逾時，改由 ping/pong 判定健康，避免安靜設備反覆離線。
3. viewer 仍無設備寫入權限，但可用有效 CSRF 正常登出與撤銷 Session。
4. inferred 唯讀狀態不因同步而改為 reported。

另加入異常 state 隔離與非有限數值過濾，以及亮度／色溫僅允許 light Entity 的映射檢查。審查者沒有讀取秘密，最終測試由主實作者執行。

## 執行環境與視覺檢查

Windows 11 x64、Python 3.14.4、Node 24.15.0。瀏覽器使用本機 Edge headless；桌面 1440px、手機 390px 截圖位於 frontend/test-results/，不提交 Git。實際檢視了截圖並確認卡片、手機控制、模式標示與待支援提示。

測試過程會操作 Mock 並留下示範紀錄，不影響任何真實電器。E2E 執行前檢查本地設定與服務均為 Mock。

## 尚未驗證

Docker／Compose 設定解析、映像建置、Python 3.12 容器、Linux arm64、樹莓派效能與備份還原；HA 實際認證／網路／配對；所有實機控制、BLE 接收、串流／PTZ／IR、能源量測與歷史。上述未完成項目不列入通過結果。

正式部署與實機測試前仍須依 SETUP_GUIDE.md、DEVICE_COMPATIBILITY.md 逐項確認，不以此測試報告推定設備支援。

## 型號更正

使用者將 P316M 更正為 P306。已更新資料、UI、設定與相容性文件；新增測試限制只有三個智慧 AC 可控制，一般 AC／未驗證 USB 不可寫，沒有功率能力或示範讀值。舊 Mock 紀錄僅保留歷史，不沿用為 P306 狀態。

## 私人發布準備（2026-10-12）

新增 HTTPS Secure Cookie 與前後端同源靜態入口，後端共 24 項測試通過，Ruff、前端 build 與本機 Edge 整合測試通過。Tailscale 已登入在線，但首次 Serve 提示帳號尚未啟用；私人 HTTPS 與手機連線等待帳號啟用後驗證，尚不宣稱發布成功。

發布結果：使用者完成 Serve／HTTPS 啟用後，私人 HTTPS 的網頁、資產、登入／登出、Secure Cookie、WSS、P306 模擬開關／還原與秘密檔 404 均通過。Serve 設定未包含公開 AllowFunnel。手機端及不同外部網路仍待使用者確認。

## 2026-10-12 本機 HA Container

已建立 Home Assistant Container 2026.10.1，Windows localhost:8123 可達，瀏覽器顯示繁體中文初次帳號設定。onboarding API 可用、未授權 states 為 401。原本自製平台維持 Mock。映像來源／摘要、腳本檢查與限制見 HOME_ASSISTANT_LOCAL.md。實體設備與授權 Token 尚待使用者設定，沒有實機成功紀錄。

後續查明 WSL 閒置結束會造成間歇中斷，已由 ha-local.ps1 Start 保留專用隱藏 WSL 程序。健康檢查先重現失敗，再修正；未呼叫 WSL、背景執行 69 秒後仍通過 HTTP 200／未授權 API 401。沒有設定 Windows 開機啟動。

## 2026-10-12 實體整合驗證補充

P306 已由使用者完成 Tapo 認證；HA UI 顯示型號／版本、3 智慧 AC／USB／夜燈狀態與控制 Entity。H110 已沿用 HA 既有授權加入，讀到網關版本與 4 個 IR 子紀錄，但沒有可用 IR 控制 Entity。UI 與唯讀 device/entity registry 已交叉核對。沒有實際切換電器或觸發紅外線。C260 停在攝影機專用帳號設定頁。平台仍是 Mock；未跑既有程式測試，因本輪未修改應用程式。詳見 LOCAL_DISCOVERY.md 與 DEVICE_COMPATIBILITY.md。

C260 後續完成登入，HA 影像播放已驗證：3840×2160、持續播放、currentTime 跨兩次讀取增加。PTZ、偵測事件未測。另準備只讀 HA 映射（3 設備／5 Entity），Pydantic MappingFile 驗證通過，沒有 writable 能力；尚未配置 HA Token，因此平台仍 Mock。


## 2026-10-12 Real Mode 只讀上線

使用者授權後，建立可個別撤銷的 HA 長效 Token `Smart Home Hub backend 2026-10-12`，由一次性 loopback 設定頁存入後端 `.env`。Token 繼承目前 HA 擁有者權限；平台白名單只讀並不會縮小 Token 本身權限。Token 未輸出至對話、前端或版本控制；一次性服務已關閉、暫存剪貼簿已清空。

已驗證 HAClient REST 取得 5 個映射 Entity，WebSocket 認證、state_changed 訂閱與初始狀態同步通過。切換 `HUB_MODE=real` 並重啟平台後，health 回報 real／integration_connected=true；登入後取得 3 台來源 home_assistant 的設備。未登入 API 回傳 401、只讀開關命令在後端回傳 422（未呼叫 HA service），Dashboard WebSocket 連線通過，API 回應不含 HA Token、entity_picture 或 RTSP URL。私人 HTTPS 網頁確認顯示 Real Mode 與 3 台設備。

P306 與 H110 當下在線；C260 在 API 探測時可用，但稍後網頁顯示待確認，仍需觀察連線穩定性。HA 播放成功不代表自製平台已有影像代理。沒有執行電器開關、PTZ、IR 或配對重置。下一步需識別可安全測試的插孔與負載，再逐項開放寫入；小米設備仍待配對與相容性驗證。


## 2026-10-12 插孔控制測試中止與更正

使用者先表示全部是安全電器，隨後補充插孔 2 為 Wi-Fi 路由器。插孔 1 關閉／恢復收到新狀態確認。插孔 2 關閉命令送出後逾時，當時 HA 仍回報測試前 on，測試工具因此跳過還原命令；後續三台 Tapo 均 unavailable，TCP 探測也失敗。因此舊報告的 restored=true 只代表當時 HA 回報，不能證明路由器實際供電恢復，已更正報告註記。

停止測試，插孔 3 未測。Dashboard 三孔仍全部 writable=false，插孔 2 列為網路基礎設備，禁止作為一般開關測試負載。需使用者在 P306 本體開啟智慧插座 2，待路由器與裝置恢復連線後重新讀取；不盲目重送命令，不宣稱實體還原完成。


## 2026-10-12 使用者恢復網路後的只讀確認

重新透過 HA REST 與 WebSocket 讀取，P306 三個智慧插孔均回報 on，H110 訊號實體回報 3；平台 health 為 real／integration_connected=true，P306 與 H110 available=true、stale=false。C260 的即時預覽實體仍 unavailable，不能宣稱攝影機恢復。此次沒有送出任何裝置控制命令。

使用者補充負載：插孔 2 為 Wi-Fi 路由器；插孔 3 為另一台電腦、螢幕、檯燈共用延長線總電源。兩孔保留只讀並排除一般開關測試／自動關閉情境，負載紀錄存於忽略版本控制的 `.local/p306-loads.json`。插孔 1 負載名稱仍待確認，平台三孔目前全部只讀。


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

最終檢查：pytest 32 項、Vitest 4 項、Ruff、ESLint、TypeScript／Vite build 通過；npm 安裝稽核 0 弱點。未切換實機隱私模式、IR 電器或任何插孔。
# 2026-10-12 小米接入補充驗證

實機檯燈透過 HA 及平台 API 的開關、亮度與色溫變更均取得狀態更新確認，已恢復原先關閉／亮度／色溫。香氛機無能力按鈕，API 操作被 422 拒絕；超出範圍色溫被 422 拒絕。詳細證據與同值命令逾時限制見 [小米整合計畫](XIAOMI_INTEGRATION_PLAN.md)。

後端 pytest 32 passed；前端 Vitest 4 passed（含新增燈具缺值顯示測試）、ESLint 與 TypeScript／Vite Build 通過。Build 仍有既有大型 JS bundle 警告。未操作 P306 插孔 2、3 或 C260 隱私模式，未驗證香氛機與溫濕度計實機控制。


## 2026-10-12 H110／C260 新增驗證

後端 34 項、前端 5 項測試通過，Ruff／ESLint／TypeScript／Vite Build 通過；上游 Tapo IR Hub 61 項測試通過。實機與私人頁面已驗證 IR 傳送，C260 ONVIF 與平台 PTZ 取得位置變化並復位，隱私恢復開啟。隱私阻擋、未授權、CSRF、未知方向、移動失敗仍停止皆有測試。完整限制與備份見 IR_PTZ_SETUP.md；未將 43 個按鍵全數標示為逐鍵實體驗證。

## C260 延遲修正（2026-10-12）

改為 LL-HLS，安全轉送 blocking reload 參數，新增回到直播與落後秒數。後端 36、前端 6 項測試通過，Lint／Build 通過。私人 HTTPS 頁面實測 readyState=4、paused=false、無 MediaError，播放器距串流最新位置約 1.9 秒；並非現場到螢幕總延遲。詳見 CAMERA_LATENCY.md。
