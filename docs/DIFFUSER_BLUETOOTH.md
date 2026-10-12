# 香氛機本機藍牙控制

2026-10-13：Windows 藍牙直連 `xiaomi.diffuser.xw2iv`／韌體 `2.1.3_3115` 已接入 FastAPI 與網頁。不透過離線的 HA 香氛機 Entity 發送控制，啟用時自動隱藏相同型號的舊卡片，避免重複。

## 已實機驗證

| 網頁功能 | 裝置屬性 | 範圍 |
| --- | --- | --- |
| 擴香開關 | 2.2 | 開／關 |
| 氛圍燈開關 | 3.1 | 開／關 |
| 出香時長 | 2.3 | 2–6 秒，間隔 1 秒 |
| 出香間隔 | 2.4 | 10、15、20 分鐘 |
| 氛圍燈亮度 | 3.2 | 1–100% |
| 氛圍燈顏色 | 3.3 | RGB，0–16777215 |
| 電池 | 5.1 | 唯讀 |

四項進階設定已各自修改、重新讀回、恢復原值並再次確認。證據在私有 `.local/diffuser-settings-verification.json`。原值為 4 秒、20 分鐘、100%、`#FAEAD3`。不是以模擬測試宣稱實機成功。

## 安裝與設定

1. 先依 README 安裝後端一般依賴，再以相同 Python 執行 `python -m pip install -r backend/requirements-ble.txt`。
2. 在不受 Git 管理的私有目錄保存 JSON，包含 `model`（固定為上述型號）、`address`（本機掃描取得的 BLE 位址）及 `ltmk`（64 字元十六進位 Mesh GATT 金鑰）。不要把這份檔案放在前端、公開目錄或日誌。
3. 在 `.env` 設定 `HUB_BLE_DIFFUSER_CONFIG` 為該檔案的絕對路徑。留空即可停用，不影響 HA 裝置整合。這台電腦已設定 `.local/diffuser-runtime.json`。
4. 使用 Real Mode 啟動一個後端程序。多個程序會競爭同一條藍牙連線，不要啟動多個 Uvicorn worker 或同時執行研究探測工具。
5. 電腦保持開機、藍牙開啟並在接收範圍內；若米家 App 占用連線，關閉 App 後等待重連。不需要解除配對或重置。

金鑰來自使用者已授權帳號的 `/v2/blemesh/query_dev` 查詢。一般 BLE 的候選金鑰不能代替本裝置的 `gatt_ltmk`。取得金鑰後，本機控制不需逐次呼叫小米雲端。

## 狀態與錯誤處理

- 唯一 BLE 工作階段負責登入、接收通知及查詢。操作與背景查詢使用同一把鎖，避免封包交錯。
- 先驗證應用層設定回覆，再主動讀回同一屬性；只有值符合才回傳 `confirmed`。傳輸 ACK 不代表操作完成。
- 實機通知可能比查詢回覆晚到，使用 64 個計數器的接收視窗允許亂序，仍拒絕重複及過舊封包。加密驗證失敗即中斷該工作階段。
- 連線失敗採 2–30 秒退避重試，不重送先前控制。每 10 秒檢查主要狀態；超過 45 秒沒有完整同步即不可操作。錯誤只記錄類型及程式位置，不記錄憑證。
- 舊研究工具保留於 `.local`，正式程式在 `backend/app/integrations/ble_diffuser.py`、`mesh_session.py`、`mesh_protocol.py`。

## 尚未完成

**定時排程尚未接入。** 目前此型號的 MIoT 屬性沒有經驗證的定時表；小米 SDK 另提供 `Service.scene` 定時場景 API，但這不證明香氛機能把排程保存於本機。未修改既有米家排程。後續優先評估將本機 BLE 控制提供給 HA 自動化；須明確處理主機睡眠、離線與漏執行，不能假裝裝置離線仍會準時執行。

來源：[小米官方 SDK 定時場景文件](https://miecosystem.github.io/miot-plugin-sdk/module-miot_service_scene.html)。

人體感應出香、自動夜燈等額外功能尚未測試寫入。樹莓派部署需另驗證 Linux／BlueZ、藍牙權限、接收距離；HA OS 本體不等於可以直接執行這個 Windows 後端，容器部署還需要正確的 D-Bus／Bluetooth 存取。勿直接把 Windows 驗證結果當成樹莓派已通過。

## 本次驗證

- 後端 pytest：58 項通過；Ruff 通過。
- 前端 Vitest：14 項通過；ESLint、TypeScript 與 Vite Build 通過。仍有既有的前端產物大小提示，未作為錯誤忽略。
- 私人 HTTPS 網頁實際操作燈光開／關、出香間隔 20 → 15 → 20，均收到 `confirmed`。
- 390 px 手機與 820 px 平板檢查未出現橫向溢出；截圖保留 `.local/diffuser-mobile.png`、`.local/diffuser-tablet.png`。
- 尚未進行多日連線耐久測試、實體手機瀏覽器相容性或樹莓派實測。前端視窗尺寸測試不等於實體 iPhone 測試。


## 公開版本注意

Repo 不包含 .local 研究工具、金鑰擷取工具或任何憑證。上述 .local 路徑僅是開發時私人證據位置，下載專案不會取得這些檔案。新使用者必須合法取得自己的 Mesh GATT 金鑰；目前不是一鍵安裝整合。尚未確認其他型號、韌體與樹莓派可用性。
