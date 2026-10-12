# 本機裝置探索結果

檢查日期：2026-10-12（Asia/Taipei）。此結果只代表當次網路可見性，不是裝置相容性判定。

## 範圍與方法

- Windows 實際 LAN：<設備內網IP>/24；本機介面為 .19 與 .95，閘道 .1。
- 僅對此 LAN 測試 TCP 80、443、554、2020、55443 是否可建立連線，沒有登入、控制或嘗試密碼。
- 使用獨立 .local/discovery-venv 的 python-kasa 0.11.0.1 執行 TP-Link UDP 廣播，以及同網段逐一探索；沒有送出設備控制命令。套件未加入應用程式相依環境。
- 在 HA 容器另測 .42 指定目標；使用已登入的 HA 介面執行 TP-Link Smart Home 空白主機自動探索。

## 觀察

- TCP 回應：只有 .1 路由器的 80／443。
- Windows 鄰居快取另見 .42，但沒有型號證據，不能認定為 P306 或其他預定設備。
- Windows TP-Link 廣播與逐一探索：沒有可識別回覆。
- HA 容器指定 .42：沒有可識別回覆。
- HA 整合精靈顯示「網路上找不到裝置」。沒有新增任何實體設備。
- 未建立 HA 平台專用 Token，未使用或擷取瀏覽器內的 Token；本平台維持 Mock。

## 下一步

1. 使用者確認設備通電、Tapo App 顯示在線，以及設備與此電腦是否同一家庭 LAN。
2. 從 Tapo App 或路由器既有 DHCP 清單取得 P306、H110、C260 IP，先指定 IP 測試；不需要重置設備。
3. Tapo 整合要求帳號驗證時，使用者直接於本機 HA 輸入 Tapo 帳密。不可把 Hub 的 admin 密碼當作 Tapo 密碼。
4. 視韌體需要確認 App 的第三方相容性設定；不因探索失敗就關閉防火牆或變更配對。
5. BLE 尚未掃描：目前 HA 沒有藍牙傳入，需另外準備 HA 可用 Bluetooth 或 ESPHome Proxy。Matter／HomeKit 多播探索亦未驗證。

官方說明確認 Tapo 需要帳號驗證，跨網段自動探索受限制，可改以 IP 加入：[HA TP-Link Smart Home](https://www.home-assistant.io/integrations/tplink/)。本次未能區分離線、網路隔離、防火牆與不同網段等原因，不把推測列為已確認原因。

詳細掃描結果保存在 Git 忽略的 .local/lan-port-discovery.json 與 .local/tplink-discovery.json，沒有密碼或 Token。

## 開啟 Tapo HA 支援後重新探索

使用者回報已在 Tapo App 開啟 HA 支援後，再次使用 Windows python-kasa 執行廣播及 <設備內網IP>/24 逐一 UDP 探索，結果仍無可識別回覆。沒有登入嘗試或控制操作，沒有新增設備。下一步需要 App 顯示的實際 P306 IP，以區分目標位址／路由可達性與認證問題；不能據此認定開啟設定失敗。

## 使用者提供 IP 後定點檢查

使用者指定 P306=<設備內網IP>、H110=<設備內網IP>（型號來自使用者，尚非設備回應確認）。Windows 與 HA 容器逐一 TP-Link 探索均無回覆；兩者 TCP 80／443 皆未建立連線，ping 皆逾時，Windows 鄰居表顯示 Incomplete／全零 MAC。對照閘道 .1 的 ping 成功。Find-NetRoute 確認目標使用 Wi-Fi <設備內網IP>、直接 <設備內網IP>/24 路由，沒有走 Tailscale。

此證據顯示當次本地可達性尚未建立，不足以判定設備不支援或帳密錯誤。需使用者確認 App 在線狀態、Wi-Fi SSID、IP 是否更新，以及路由器既有的訪客／IoT 隔離設定。本次未變更網路設定。

使用者確認設備連線至「mk house iot」，Windows 實際 SSID 為 你的家庭網路。不同 SSID 的互通／隔離尚待驗證。HA 指定 P306 IP 後進入認證表單，但檢查安裝版本 config_flow 顯示：探索無結果、無憑證而嘗試連線失敗時，也可能轉入此認證步驟。因此不能把表單出現視為已識別 P306。未提交帳密，未新增成功；已詢問使用者是否允許暫時將電腦 Wi-Fi 切至 IoT 網路，尚未執行切換。

使用者提供攝影機 IP <設備內網IP>（預定型號 C260，尚無設備回應確認）。Windows 定點測試 TCP 80／443／554／2020／8080 全部無法建立連線；TP-Link 探索無回覆，鄰居表為 Incomplete／全零 MAC。此時未切換 Wi-Fi，無法據此判定 RTSP／ONVIF 不支援或未啟用。未嘗試帳密、未取得影像、未移動鏡頭或變更隱私設定。

## 使用者調整 IoT 網路存取後：已確認可達

使用者回報已允許 IoT 網路存取私人網路後，保留電腦原有 你的家庭網路 連線重新定點測試，Windows 與 HA 容器均收到以下 TP-Link 探索回覆：

| IP | 設備實際探索型號 | 類別 | 已確認連線 |
| --- | --- | --- | --- |
| <設備內網IP> | P306(US) | SMART.TAPOPLUG | TP-Link 探索、TCP 80 |
| <設備內網IP> | H110(US) | SMART.TAPOHUB | TP-Link 探索、TCP 80 |
| <設備內網IP> | C260 | SMART.IPCAMERA | TP-Link 探索、TCP 443／554／2020 |

硬體版本與韌體版本尚未從此次探索取得。RTSP／ONVIF 連接埠可達不代表影像播放、PTZ 或事件已驗證。尚未取得已授權裝置資訊、匯入設備或操作插孔。

HA P306 認證表單仍顯示先前 try_connect_all failed；請使用者在本機頁面確認 Tapo 帳號密碼後重新傳送。本次不讀取、輸出或複製表單秘密。平台維持 Mock，沒有重置、重新配對或修改電腦 Wi-Fi。

## HA 認證完成後實體整合結果

2026-10-12：使用者完成 P306 Tapo 認證，已在 HA UI 與唯讀 device/entity registry 交叉確認。

- P306：硬體 1.0；韌體 1.1.2 Build 240531 Rel.204226。HA 顯示主裝置及五個子裝置紀錄，共 40 個實體；這不是六台實體延長線。已讀到三個智慧插孔、USB 群組與夜燈控制實體及目前狀態，尚未操作開關。所有 P306 實體（含停用者）未見功率或用電量測 Entity。
- 主控制 Entity：switch.p306_zhi_hui_cha_zuo_1／2／3、switch.p306_usb_lian_jie_bu、light.p306_ye_deng。沒有一般 AC 插孔的可控 Entity。未變更更新設定、LED 或自動關閉設定。
- H110：利用 HA 已有 Tapo 授權加入成功；硬體 1.0；韌體 1.5.4 Build 260725 Rel.042648。主裝置加四個既有 IR 遙控器紀錄，共 22 個實體。網關有警報、LED 與診斷實體，但未執行操作。四個 IR 子紀錄僅各有停用的 restart／unpair 管理實體，沒有可用 IR 控制 Entity，不能宣稱紅外線已支援。沒有新增或解除原 App 子裝置配對。
- C260：指定 IP 並使用 HA 既有 Tapo 授權後，流程已到「設定攝影機帳號憑證」。尚待使用者在 HA 輸入攝影機專用帳密，或自行選擇略過即時預覽；目前尚未完成 C260 新增。沒有取得影像、移動 PTZ 或改隱私設定。
- 自製平台仍維持 Mock；尚未配置平台專用 HA Token 或啟用 Real Mode。HA 已完成整合與自製平台取得真實狀態是不同驗證步驟。

## C260 完成登入與 HA 影像驗證

2026-10-12：使用者在 HA 完成攝影機專用帳號登入，HA 內建 TP-Link 整合已建立 C260 與 16 個實體。硬體 1.0、韌體 1.3.2 Build 260902 Rel.25093n。唯讀 registry 與 HA 裝置頁交叉確認。

- camera.tapo_c260_live_view 已啟用。打開預覽初期顯示「無法播放媒體」，HA 日誌出現 FFmpeg 擷取影像逾時；未變更設定後，播放器開始正常播放。可確認後續播放恢復，尚不能把初期錯誤歸因於單一原因。
- 瀏覽器主 video：3840×2160、readyState=4、paused=false；兩次觀察 currentTime 從 45.50 秒增加至 133.54 秒，沒有 MediaError。確認 HA 內即時串流持續播放，不是靜態縮圖。未下載影像、截圖或輸出原始串流 URL。
- 匯出左右／上下旋轉 button、旋轉角度 number 及偵測設定 switch。沒有操作 PTZ、隱私、偵測或 LED；控制 Entity 匯出不代表動作通過。
- 偵測設定 switch 只表示開關設定，沒有據此宣稱已收到動作、人員、哭聲等事件。本輪走 TP-Link 原生整合，尚未驗證 ONVIF Profile、ONVIF PTZ 或 topic。
- 三台設備現均已加入 HA。自製平台仍 Mock，HA_TOKEN 尚未配置，攝影機在自製平台的授權串流代理尚未實作。

## 下一步：自製平台只讀連線

已準備 .local/ha-mapping.readonly.json，含 P306 三個智慧 AC 狀態、H110 訊號狀態及 C260 camera 狀態，共 3 個設備／5 個 Entity；已經 MappingFile 驗證且無 writable 能力。USB／夜燈與影像目前仍在 HA 介面使用，沒有把它們錯標為額外 AC 插孔或在自製平台宣稱可播放。

由使用者依 SETUP_GUIDE 建立平台專用非管理員 HA 帳號，登入後在個人檔案的安全性／長期存取權杖建立 Token，只填入專案 .env 的 HA_TOKEN，不貼到聊天。後續才設定 HA_URL=http://127.0.0.1:8123、HUB_MAPPING_FILE 為該只讀映射絕對路徑，驗證 REST／WS 後切換 real。尚未自動切換或放行寫入。


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
