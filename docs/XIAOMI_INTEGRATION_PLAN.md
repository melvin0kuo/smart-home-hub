# 小米生態整合研究與接入順序

**最新狀態：2026-10-12 已完成官方 Xiaomi Home 接入，檯燈已在自製平台通過開關、亮度與色溫操作確認。香氛機僅完成實體建立，目前不可用；溫濕度計尚未接入。以下前段保留研究歷程，最新驗證見文末。**

調查日期：2026-10-12。這輪完成文件、已安裝套件與本機唯讀檢查；**尚未接入或控制任何小米實機**。

## 已知環境與使用者資訊

- 米家 App 地區：台灣。檯燈 1S：`<設備內網IP>`，已加入 Apple「家庭」，維持原配對。
- 檯燈標籤型號、硬體、韌體尚未取得。溫濕度計與香氛機的實際標籤仍待核對，研究型號分別為 MJWSD05MMC、MJXFJ03XW。
- HA Container 2026.10.1 位於 WSL2 Docker。HA REST 回應 200；目前沒有已設定的 Xiaomi Home、Xiaomi BLE、Yeelight、HomeKit Device、Bluetooth 或 ESPHome 整合。
- Windows 的 Intel Wireless Bluetooth 狀態正常，但 HA 容器的 `/sys/class/bluetooth` 沒有介面、沒有 D-Bus 掛載。Windows 有藍牙不等於 HA 能使用。
- HA 已安裝 `xiaomi-ble==1.16.1`；未安裝官方 `xiaomi_home` 自訂整合。

## 相容性與建議

| 設備 | 本輪證據 | 目前障礙 | 接入路線 | 驗證狀態 |
| --- | --- | --- | --- | --- |
| 檯燈 1S | 指定 IP 的 TCP 80 可連；55443 與 443 在 2 秒連線測試逾時 | 尚未讀到設備型號或燈光狀態；HomeKit 已在 Apple 家庭 | 先確認 Yeelight App 是否提供 LAN Control；若不適用，再評估 Xiaomi Home OAuth；HomeKit 遷移需另行同意 | 文件有路線，未接入 |
| 溫濕度計 3 | 現有解析器 `devices.py` 明列 MJWSD05MMC 的 product ID `0x2832`、`0x4C47` | HA 沒有可用藍牙接收器；標籤、加密與廣播內容未實測 | HA Xiaomi BLE + ESPHome Bluetooth Proxy，或未來樹莓派 HA 可用藍牙 | 程式碼確認型號辨識，感測值待實測 |
| 智慧香氛機 | XiaomiGateway3 原始碼明列 MJXFJ03XW，具有擴香與燈光等映射 | 需要適用的小米網關與韌體；目前沒有已確認可用網關；實際型號未知 | XiaomiGateway3 作為研究候選；現階段保留待支援紀錄 | 社群程式碼有證據，實機未驗證 |

TCP 80 回應只代表指定 IP 的服務可達，不能證明裝置身分或控制成功。55443 逾時也不能單獨證明韌體不支援 LAN Control，可能涉及設定或防火牆。這輪沒有送出燈光寫入命令。

## 檯燈：先保留 Apple 家庭

HomeKit Device 的官方流程要求配件尚未配對其他控制器。現有配對不直接加入 HA；若未來選擇遷移，需明確同意移除原配件，再由 HA HomeKit Bridge 回送 Apple 家庭。既有自動化與家庭成員設定可能需調整。[HomeKit Device](https://www.home-assistant.io/integrations/homekit_controller/)、[HomeKit Bridge](https://www.home-assistant.io/integrations/homekit/)。

Yeelight 是可研究的本地備選，須先核對標籤與韌體，以及 App 是否真的提供 LAN Control。HA 清單有其他米家檯燈，但不能據此宣告本台 1S 支援。這輪指定 IP 的 55443 無法連線，尚未取得 `power`、亮度或色溫。[HA Yeelight](https://www.home-assistant.io/integrations/yeelight/)。

官方 Xiaomi Home 是另一條備選，須安裝自訂整合並透過官方登入授權。程式提供 `cn/de/i2/ru/sg/us` 伺服器，沒有獨立 `tw` 選項；專案討論的登入地區對照將 TW 歸入 Singapore，可先以 `sg` 作候選，**仍須以授權後實際裝置清單確認資料所在伺服器**。登入地區與裝置雲端資料區不宜直接畫上等號；不要求使用者改變米家 App 的台灣地區或重新配對。[官方專案](https://github.com/XiaoMi/ha_xiaomi_home)、[伺服器常數](https://github.com/XiaoMi/ha_xiaomi_home/blob/main/custom_components/xiaomi_home/miot/const.py)、[地區對照討論](https://github.com/XiaoMi/ha_xiaomi_home/discussions/1606)。

沒有適用中樞時，官方整合控制通常經雲端；其實驗性 LAN Control 官方不建議啟用。內建 `xiaomi_miio` 與官方自訂 `xiaomi_home` 是不同整合，不以同名推定支援本檯燈。

## 溫濕度計：解析器已準備，接收路徑未準備

本機套件已具備上述兩個 product ID。上游 v1.15.0 亦明載新增 MJWSD05MMC 的新版硬體 ID `0x4C47`，更正初期報告「尚未取得明確型號支援證據」的結論。[上游版本紀錄](https://github.com/Bluetooth-Devices/xiaomi-ble/releases/tag/v1.15.0)。

建議先使用網路型 ESPHome Bluetooth Proxy，避免先改動 Windows 內建藍牙的使用方式；這是部署建議，尚未購買或設定。若改用 USB 藍牙，需完成 WSL USB 直通、Linux BlueZ、D-Bus 與容器權限設定，不能只插上就視為完成。未來移至樹莓派再確認內建藍牙與覆蓋距離。[HA Bluetooth](https://www.home-assistant.io/integrations/bluetooth/)、[ESPHome Proxy](https://esphome.io/components/bluetooth_proxy/)。

收到封包後才確認是否需要 Bindkey，並驗證溫度、濕度、電池與時間戳。電池可能較晚才廣播。若需密鑰，優先採用 HA Xiaomi BLE 文件提供的 Xiaomi Cloud 匯入流程；不刷韌體、不啟用會改變既有 Bindkey 的工具。至少觀察 24 小時接收穩定性。[Xiaomi BLE](https://www.home-assistant.io/integrations/xiaomi_ble/)。

## 香氛機：已有候選，但不能直接當一般 BLE 感測器

XiaomiGateway3 的 `devices.py` 列出 MJXFJ03XW 的 `xiaomi.diffuser.xw002` 與 `xiaomi.diffuser.02wh`，並定義擴香開關、持續／間隔、燈光、電池等 MIoT 映射。不同 product ID 的設定有差異，須核對實機後逐項驗證。[整合原始碼](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/core/devices.py)。

該路線依賴其支援的小米多模網關／Aqara 網關與指定韌體。整合會啟用網關 Telnet 並執行代理程式；新版韌體可能需要額外處理。因此不直接安裝到未知網關、不要求降版或拆機，也不先推薦購買未核對韌體的產品。[XiaomiGateway3](https://github.com/AlexxIT/XiaomiGateway3)。

Tapo H110 不在此路線的支援網關內。ESPHome Bluetooth Proxy 與 Xiaomi BLE 被動解析也不能自動代替香氛機的控制協定。官方 Xiaomi Home FAQ 明確排除 Bluetooth 類別，不能期待單靠 OAuth 就接入這台香氛機。現階段平台仍不開放擴香或燈光按鈕。

## 下一步與實測放行條件

1. 先取得檯燈標籤型號與韌體，確認 Yeelight App 既有設備頁是否有 LAN Control；不重置、不移除 Apple 家庭。
2. 若無可用本地控制，準備固定版本的官方 Xiaomi Home 自訂整合，再由使用者完成官方 OAuth，核對台灣帳號的實際清單。此輪尚未安裝。
3. 確認溫濕度計與香氛機標籤及韌體；盤點是否已有小米網關及型號。沒有網關不妨礙先做檯燈與溫濕度計。
4. 決定 BLE 接收方案並收到真實封包，才加入溫濕度、濕度與電池 Entity 映射。
5. 每台只建立一筆平台裝置；控制能力經實測才設為 verified。檯燈開關、亮度及色溫各自確認；讀取 HA 宣告範圍，不硬編固定值。

本輪只修改研究文件，未更動服務、現有設備映射、帳號授權、配對、網路或韌體，未重跑應用程式測試。HA API、指定 IP 連線與容器套件檢查結果已記錄於上文。

## 2026-10-12 接續安裝紀錄

使用者指示直接處理後，已從官方 GitHub 取得穩定版本 `v0.5.0`（commit `75b3acb6325a3a8d295688b13904737d6738a6a5`），檢查 manifest 與安裝腳本，再直接複製 `custom_components/xiaomi_home` 至 HA 設定目錄，沒有執行腳本中的刪除操作。

安裝前正常停止 HA，完整設定備份保存在 Linux `/home/<你的使用者>/smart-home-hub-ha/backups/pre-xiaomi-complete-20261012-030840.tar.gz`，檔案權限 0600、目錄 0700，內含秘密，不提交 Git。首次以一般使用者備份因 auth 權限失敗，該不完整檔案不可用於還原；上述帶 complete 的備份才是完整備份。

重新啟動後，HA 已顯示官方 Xiaomi Home 設定助理；HA 授權 API 回應 200，自製平台健康檢查回應 200、Real Mode、integration_connected=true。現有 Tapo 映射與設備配對未修改。

目前停在「風險告知」頁，等待使用者親自確認後繼續。尚未完成小米 OAuth、選取裝置、建立 Entity 或任何小米控制測試。後續需檢查登入回呼位址在此 Windows／WSL 網路是否可達；不預設 homeassistant.local 已可解析。

接續：使用者已親自同意風險並按下一步。已設定 Singapore 候選伺服器與繁體中文，產生 OAuth 流程並開啟 `account.xiaomi.com` 官方登入頁，等待使用者登入及確認權限。Windows 對 `homeassistant.local` 的名稱解析失敗；登入回呼尚待處理。若回呼分頁保留有效參數，可在本機將同一回呼導向既有 HA loopback 服務，保留原路徑與參數；不得將授權碼輸出至日誌、文件或聊天。尚未宣告小米實機接入成功。

使用者回覆已登入並授權後，HA 設定助理仍等待回呼。登入分頁已變成瀏覽器連線錯誤頁；瀏覽器安全規則禁止代理讀取該頁，停止自動讀取，請使用者在本機將原回呼網址的主機改為 `127.0.0.1`，其餘路徑與參數保留。未修改 hosts、網路設定或授權驗證邏輯；尚未完成裝置匯入。

後續經使用者明確同意並確認 Windows 管理員提示，已先備份 hosts，再加入唯一一筆 `127.0.0.1 homeassistant.local`。Windows 名稱解析與 HTTP 200 驗證通過。此設定只適用目前電腦，移植樹莓派時需重新評估名稱對應。

重新授權後遇到 `already_in_progress`。更正前述「原流程已關閉」的推論：關閉 UI 不等於清除 HA 內的使用者流程；HA `config_entries/flow/progress` 明確排除 SOURCE_USER，空清單不能當作沒有使用者流程。官方整合在同帳號 `async_set_unique_id` 檢查時因另一流程而中止，日誌確認此錯誤。已安排正常重新啟動 HA 清除暫存流程，後續只保留單一設定程序。尚未把此次授權當成裝置匯入成功。

## 最新實測結果

清除舊流程並由使用者重新確認授權後，Singapore 伺服器成功列出 4 台米家設備。只選取目前房間的檯燈與香氛機；其他家庭的攝影機及溫濕度計未匯入，不因雲端可見而推定本地藍牙可接收。

| 設備 | HA 取得的型號／韌體 | 匯入結果 | 平台能力 |
| --- | --- | --- | --- |
| 米家檯燈 1S | yeelink.light.lamp4／2.1.7_0020 | 5 個 Entity，主 light 可讀取 on/off | 開關、1–100% 亮度、HA 宣告的 2600–5000 K 色溫已驗證 |
| 小米智慧香氛機 | xiaomi.diffuser.xw2iv／2.1.3_3115 | 15 個 Entity，全部 unavailable | 只建立待確認紀錄，無操作按鈕 |
| 溫濕度計 3 | 雲端識別 xiaomi.sensor_ht.o3；標籤／韌體待核對 | 未匯入；位於另一個米家房間 | 未提供感測值 |

硬體版本及商品標籤仍未知；上表是設備註冊與雲端資料，不能替代實體標籤。帳號清單將香氛機列為 BLE-Mesh，與初期以一般 BLE／MJXFJ03XW 研究的假設不同。官方專案 FAQ 對 Bluetooth 類別的排除不能蓋過實際匯入證據，但 Entity 存在也不代表實機可控制。需確認此區域型號的相容 BLE-Mesh 網關、供電與米家 App 遠端連線情況；不要求先買網關，不嘗試未知寫入。

控制模式明確選擇雲端，未啟用實驗性 LAN 控制，未修改 Apple 家庭配對。因此目前檯燈依賴小米雲端，不能標示為純本地。

### 驗證與限制

- 先透過 HA 操作檯燈，取得開啟、亮度及色溫變更、恢復及關閉的更新確認；原先關閉，開啟後讀到亮度 161/255、色溫 5000 K，測試後恢復。
- 再透過自製平台登入、CSRF 與 `/api/devices/real-xiaomi-lamp1s/actions` 測試上述操作，均回應 confirmed；這是 HA 設備回報確認，未以獨立光感測器驗證光輸出。
- 香氛機操作與超出範圍的色溫均回應 422；P306 插孔 2、3 未操作，C260 隱私模式未切換。
- 第一輪平台測試的清理程式重複送出已恢復的相同數值，因沒有新事件而逾時；立即透過 HA 恢復關閉。修正測試清理程序後，實際有變更的所有動作通過。既有「相同值可能因沒有新事件而逾時」限制未改動，不能宣告已解決。
- 修正頁面：缺少亮度／色溫回報時顯示「尚未回報」並停用滑桿，避免以最小值假冒實測值。開燈取得回報後才可調整。
- 即時映射在私有 `.local/ha-mapping.active.json`，修改前已備份；新增 real-xiaomi-lamp1s 與 real-xiaomi-diffuser，保留原 Tapo 映射。
- 官方整合另有 HA 2027.7 將不再支援的 device_tracker 屬性警告；目前檯燈操作不受影響，未來升級 HA 前需檢查上游修正。
