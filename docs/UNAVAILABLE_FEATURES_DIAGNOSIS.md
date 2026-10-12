# 尚未可用功能：原因調查與解決路線

調查日期：2026-10-12。此份為目前最新診斷，補充先前文件中的歷史紀錄。只進行授權 API、設備唯讀查詢及上游原始碼查核；沒有操作插孔、發送 IR、移動鏡頭、關閉隱私、修改網路或裝置配對。

後續進度：使用者授權開始處理後，H110 三組遙控器及 C260 PTZ 已接入平台並進行傳送／位置測試，詳細結果見 [安裝與實測紀錄](IR_PTZ_SETUP.md)。下文保留研究當時狀態。使用者另確認附近沒有小米／藍牙網關。

## 決策摘要

| 項目 | 本機／實機證據 | 目前判斷 | 解決路線與驗收 |
| --- | --- | --- | --- |
| H110 紅外線 | HA 沒有 remote Entity；直接本地查詢取得四組 IR 子紀錄，key_list 長度依序為 13、6、0、26 | 原生整合未提供控制介面；不是完全沒有既存遙控資料 | 優先評估 Tapo IR Hub v2.1.0 的共享 TP-Link 連線；先備份、審查完整套件及測試，再只匯入既存資料。逐個按鍵經實測才加入平台白名單 |
| C260 PTZ | ONVIF 認證及 GetProfiles／GetNodes／GetStatus 成功；宣告連續及相對水平／垂直移動；尚無 ONVIF 設定項目 | 具備接入條件，仍缺 HA 整合、平台控制路徑與有限移動驗證 | 加入 ONVIF，保留目前唯一攝影機卡片及影像來源；驗證有限移動與停止後才開按鈕 |
| 小米香氛機 | xiaomi.diffuser.xw2iv，韌體 2.1.3_3115；HA 15 個 Entity 全部 unavailable；即時小米雲端清單 online=false | 上游連線離線，不是單純前端按鈕問題；Mesh 網關缺少或不可用仍屬待確認假設 | 先確認供電、米家 App 關閉手機藍牙後是否可控制、相容 Mesh 網關及其地區／韌體。恢復雲端在線後重查現有官方整合 |
| 溫濕度計 3 | 雲端 xiaomi.sensor_ht.o3，韌體 2.0.0_0005、online=false；HA 容器藍牙介面數 0；無 Bluetooth／ESPHome 設定項目 | 目前沒有 HA 可用的 BLE 接收通道；是否放在另一住處待本人確認 | 確認標籤及實際位置；已有相容 ESP32 可建 ESPHome Bluetooth Proxy，或樹莓派 HA OS 藍牙。收到封包後確認 Bindkey 與感測 Entity |
| P306 用電資訊 | 現有整合沒有功率／電量 Entity；本機型與最初 P316M 不同 | 沒有量測能力證據，無法靠 UI 產生實際用電數值 | 保持能源功能停用；若確定需要，另核對具有量測能力的硬體與負載規格 |

以上「解決路線」均不是完成宣告。使用者尚未回覆的硬體與位置問題，不以推測填寫。

## H110：已有可讀資料，缺控制橋接

HA 使用 python-kasa 0.11.0.1。唯讀連線採用 HA 已保存的連線參數與憑證雜湊，僅在記憶體使用，不寫出秘密。第一次探索程式誤將 HA 設定直接當 DeviceConfig，以及將 children 當字典；修正參數轉換與清單處理後查詢成功，這兩次程式錯誤不當作裝置不支援的證據。

四組既存資料與先前盤點的機上盒、風扇、冷氣、電視相符。三組有 key_list；冷氣有 ac_status／ac_mode／hexData 等整組狀態欄位，key_list 為空不能解釋成冷氣沒有控制能力。原始 IR 碼、裝置識別碼與憑證未加入本報告。

新候選 [Loadst0ne/tapo-ir-hub](https://github.com/Loadst0ne/tapo-ir-hub) 的 [v2.1.0](https://github.com/Loadst0ne/tapo-ir-hub/releases/tag/v2.1.0) 發布於 2026-09-05，要求 HA 2026.8 以上；目前 HA 2026.10.1 符合版本門檻。原始碼 shared_api.py 使用既有 TP-Link coordinator，從 child 資料讀取遙控清單，並能建立 remote.send_command 路線。manifest 另外要求 plugp100>=5.1.7,<7.0.0.dev0，即使採共享連線也要評估依賴衝突。

本輪只下載部分固定版本原始碼至忽略的 .local/research 供審查，未安裝至 HA。原始碼與 README 宣告不等於這台韌體已實測；版本紀錄亦明載發版檢查未發送實體 IR。後續應取得完整固定 commit、檢查啟動時不寫入設備、不自動重送控制、移除時不刪機上遙控資料，再備份與安裝驗證。先不暴露新增、刪除、學習、重新配對等管理功能。

IR 為單向傳送。成功發送只能顯示「已送出」，不能當作電器已回報真實狀態；冷氣不可猜測缺少的整組設定，也不能把設定溫度當室溫。

另一條路線為 Matter Bridge。TP-Link [2026 官方介紹](https://community.tp-link.com/en/home/forum/topic/855696) 說明 IR 可匯出基本電源控制；[2025 舊討論](https://community.tp-link.com/en/home/forum/topic/829318) 則仍顯示當時不支援，兩者反映時間／韌體差異，不以舊結論否定新版，也不以新版說明保證本機可用。現有 WSL NAT／Docker bridge 未部署 Matter Server、IPv6／mDNS 未驗證，因此先採可利用既有本地連線的軟體候選。Matter 配對若需要變更既有配對，另依使用者授權規則處理。[HA Matter](https://www.home-assistant.io/integrations/matter/)。

上游 [python-kasa PR #1716](https://github.com/python-kasa/python-kasa/pull/1716) 仍為 open，研究 H110 冷氣狀態控制；不能把未合併的程式當成目前 HA 已支援，也不直接覆蓋 HA 套件。

## C260：ONVIF 唯讀檢查通過

沿用 HA 已保存的攝影機專用帳密，在容器內記憶體完成連線；未輸出帳密或帶認證的串流網址。

- TCP 2020、554 可達。
- GetProfiles：mainStream、minorStream 為 H264，jpegStream 為 JPEG；三個 profile 都有 PTZ configuration。
- GetNodes：連續與相對 PanTilt 空間均存在；MaximumNumberOfPresets=8、HomeSupported=false。這是設備宣告，不是實測可用預設點數。
- GetStatus：成功取得位置，Error 字串為 `0`。先前以 bool(Error) 判斷會將此非空字串誤認為錯誤；此結果不得寫成 PTZ 故障。
- 隱私控制仍為 off（攝影機停用／隱私開啟），本輪保留原狀，沒有 Move／Stop 寫入。

[HA ONVIF](https://www.home-assistant.io/integrations/onvif/) 提供 onvif.ptz。下一輪先加入 HA ONVIF，再驗證有限時長移動與停止、防重複請求、離線／隱私阻擋，才新增後端能力與前端按鈕。單純讀到 PTZ configuration 不升級為 verified。沒有實測 zoom；不提供猜測的縮放或回原點控制。動作／AI 事件仍需獨立驗證，不由 PTZ 結果推定。

## 香氛機：先恢復上游連線

使用既有官方 Xiaomi Home OAuth，在記憶體讀取授權，透過 MIoTHttpClient.get_devices_async 唯讀刷新帳號清單。檯燈 online=true、香氛機 online=false；證明本次雲端呼叫可用，但不能因此斷言香氛機硬體故障。帳號此次可見四台設備，沒有網關型號，不能排除其他帳號或未授權家庭中已有網關。

需使用者確認：香氛機是否開機／充電、關閉手機藍牙後是否仍可從米家操作、是否有小米 BLE-Mesh 網關及型號。若只靠手機藍牙可控，先補相容網關路徑；不盲目重新授權或重裝 HA。

若恢復在線仍無法取得屬性，再比較米家 App 與 HA 的同一 MIoT 屬性回報、整合日誌錯誤碼及模型映射。上游 [XiaomiGateway3 裝置表](https://github.com/AlexxIT/XiaomiGateway3/blob/master/DEVICES.md) 已列 xiaomi.diffuser.xw2iv，可作備援；但需要它支援的網關／韌體，涉及 Telnet 與代理程式，不能視為任意 BLE Proxy 可替代，也不先要求買網關、降版或拆機。[專案限制](https://github.com/AlexxIT/XiaomiGateway3)。

## 溫濕度計：先補接收位置與通道

新的雲端讀取取得韌體 2.0.0_0005，但實體標籤及硬體版本仍待核對。雲端房間與電腦目前房間不同，不能只依名稱判斷實際放置地點。BLE 設備的雲端 online=false 也不代表現場無法接收廣播。

目前容器沒有藍牙介面，因此先確認附近是否已有 ESPHome Proxy／可用 ESP32。後續需確認 [Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy/) 連線、[Xiaomi BLE](https://www.home-assistant.io/integrations/xiaomi_ble/) 收到封包、需要時安全匯入 Bindkey，並連續觀察接收穩定性。未來樹莓派 HA OS 可減少 WSL USB／BlueZ／D-Bus 的設定，但仍需測試距離與干擾。此路線與香氛機的 BLE-Mesh 控制分開驗證。

## 下一輪優先順序與本輪交付範圍

1. H110：審查並測試完整固定版本候選、備份後匯入現有遙控資料；先不試送未知按鍵。
2. C260：加入 ONVIF，實測有限移動／停止後擴充平台 PTZ。
3. 香氛機：取得 App 遠端控制與網關資訊，確認上游離線原因再選整合。
4. 溫濕度計：取得位置／標籤與 BLE 接收方案；沒有真實讀值前維持待支援。

本輪沒有修改應用程式、設備映射或服務設定，未重跑整套單元測試／Build。已實際執行 HA 狀態讀取、小米雲端清單更新、H110 本地唯讀子設備查詢、C260 ONVIF 唯讀查詢，以及容器藍牙／整合盤點。未將研究成功列為控制功能完成。
