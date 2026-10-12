# Windows 藍牙香氛機實測

日期：2026-10-13（台灣）。最新進度：已完成 Mesh 直連登入與部分真實狀態接收；平台控制能力仍依後續實測開放。

## 結果

- Windows Intel Wireless Bluetooth 介面與藍牙服務正常。
- 透過獨立 `.local/ble-probe-venv` 的 Bleak 3.0.1／WinRT 3.2.1 進行30秒BLE廣播掃描，收到31個裝置，其中1個符合香氛機識別。
- 廣播名稱 `xiaomi.diffuser.xw2iv`，MiBeacon產品識別碼20199，接收訊號約−54 dBm。名稱、產品碼與HA先前匯入型號一致；商品標籤及硬體版仍未核對。
- 使用 `pair=False` 成功建立GATT連線並列舉服務，結束後自動斷線。取得標準Generic Access／Generic Attribute、小米FE95及A00A服務。
- 此次未要求OS配對，未讀取未知特徵內容，沒有應用層GATT寫入、擴香／燈光控制、韌體更新、重置或重新配對。

## 可以與不可以推論的事

已證明：這台電腦的藍牙收得到並可連上此型號，先前「HA容器沒有藍牙介面」不代表Windows本機完全無法接觸裝置。

尚未證明：能解密應用資料、完成小米鑑權、讀取電量／擴香狀態，或控制香氛與燈光。FE95及可寫入特徵的存在，不代表可以套用一般開關命令。社群將此型號列於Mesh裝置表；此次沒有取得標準Mesh Proxy服務的證據，也不能由此推論它一定不能透過其他小米服務控制。

Home Assistant Xiaomi BLE官方明確不支援BLE Mesh；Windows成功連線不會自動使WSL中的HA具備藍牙或使原本unavailable實體恢復。既有平台仍保留待支援狀態。

## 下一步

1. 研究此型號與既有配對相容的鑑權／控制協定及仍維護的實作，確認所需憑證種類；不可將雲端Token或Bindkey直接視為通用Mesh控制金鑰。
2. 找到可靠實作後，先讀取單一狀態並驗證，才測試已知的擴香／燈光指令。沒有可靠路徑前不向未知可寫入特徵送值。
3. 若Windows直連沒有可維護實作，再評估此區域型號相容的小米Mesh網關與XiaomiGateway3；尚未要求購買硬體。

原始廣播（包含附近裝置位址）及GATT結果只保存於Git忽略的`.local/`，不放到前端或公開文件。掃描工具為本機探測原型，不是正式Provider，不與平台啟動流程綁定。

## 後續直連登入實測（2026-10-13）

使用者要求繼續嘗試控制後，已完成下列實測：

1. 讀取 FE95／0004，實機回報韌體 `2.1.3_3115`。
2. 依公開小米 Mesh 登入 PoC，送出 A4 傳輸協商並回送兩個協商封包，收到 6 與 244 位元組回覆。這是傳輸層寫入，不是擴香／燈光操作。
3. 使用小米官方登入流程，透過社群已實作的 `share/askbluetoothkey` 查詢此裝置，取得 32 位元組**候選登入金鑰**，僅保存於 `.local/diffuser-ble-key.json`。此端點不是 HA OAuth API，不能把兩種 Token 混用。查詢成功不代表金鑰適用此型號的 Mesh 登入。
4. 透過既有 HA OAuth 的 `device_list_page` 唯讀查詢，確認雲端裝置 MAC 與 Windows 掃描位址一致；公開報告不記錄位址。
5. 使用者關閉手機藍牙後，電腦成功完成 Mesh `50` 登入的 P-256 公鑰交換與傳輸 ACK。送出登入證明後收到 `52 00 00 00`，未取得參考實作要求的成功回覆 `51 00 00 00`。**登入未成功，沒有取得已驗證控制工作階段。**
6. 以非設備的合成測試向量，交叉比對 Python cryptography 與 Node.js crypto 的 HKDF-SHA256、AES-CCM 結果，兩者一致。這只排除基本加密函式不一致，不能證明選用的金鑰、CRC 範圍或完整登入流程符合這台設備。

目前可以定位失敗在登入證明確認階段；尚不能單憑 `52` 斷定是候選金鑰種類不符、裝置端金鑰不同步或韌體協定差異。未重試未知控制封包、未綁定／解除配對／重置／更新韌體。擴香、燈光、電量與狀態讀回均仍待驗證，平台控制能力維持未啟用。

### 可接續的方向

- 對照此型號的米家外掛與實際登入流程，核對 Mesh GATT 金鑰來源及登入證明格式。現有候選金鑰仍標記 `verified_on_device: false`。
- 若有可用 Android 測試手機，可研究官方 App 的登入與控制通訊；使用者目前使用 iPhone／iPad，未要求其越獄、裝憑證或重置設備。
- 使用 XiaomiGateway3 裝置表已包含此型號的相容 Mesh 網關路徑。必須再確認網關具體型號、區域及韌體，不能宣稱任何小米／Aqara 網關都相容，也尚未要求使用者購買。

暫用登入服務只綁定 `127.0.0.1:8766`，金鑰取得後已停止。雲端登入工作階段沒有寫入磁碟；候選金鑰與診斷原型均在 Git 忽略目錄。正式平台程式與設備配對設定未更動。

診斷證據：`.local/ble-transport-result.json`、`.local/diffuser-auth-result.json`、`.local/diffuser-identity-check.json`、`.local/diffuser-crypto-check.json`。原型不是可部署整合，不應隨平台自動啟動。

研究來源：

- [小米官方 Mesh 開發文件：GATT 直連須先登入](https://github.com/MiEcosystem/miio_open/blob/master/ble/04-%E8%93%9D%E7%89%99Mesh%E6%8E%A5%E5%85%A5%E5%BC%80%E5%8F%91.md)
- [Mesh 登入參考 PoC：P-256、LTMK 與登入證明](https://gist.github.com/kabbi/242a48dde4d3ae548f6d54cf1f987776)
- [小米雲端 QR 登入參考實作](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor/blob/master/token_extractor.py)
- [候選金鑰查詢參考實作：僅參考雲端端點，不代表香氛機相容](https://github.com/desperado0044/xiaomi-scooter-link/blob/master/android-app/app/src/main/java/com/scooterre/client/cloud/XiaomiCloudClient.kt)

## 來源

- [Bleak Windows後端](https://bleak.readthedocs.io/en/stable/backends/windows.html)
- [Home Assistant Xiaomi BLE支援界線](https://www.home-assistant.io/integrations/xiaomi_ble/)
- [XiaomiGateway3裝置表原始碼（20199／xw2iv）](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/core/devices.py)

## 登入問題已解決（2026-10-13 後續）

前述 `52 00 00 00` 失敗已有實證解答：先前從一般藍牙 `share/askbluetoothkey` 取得的候選金鑰不適用這台香氛機的 Mesh 管理者登入。

1. Telink 官方公開 SDK 的 `mible_mesh_auth.h` 將 `0x52` 定義為 `MESH_ADMIN_INVALID_LTMK`，`0x51` 為 `MESH_ADMIN_LOGIN_SUCCESS`。
2. 從小米官方應用商店下載米家 Android 11.7.709，僅在本機靜態檢視協定流程，沒有安裝或執行 APK。官方程式的 Mesh 連線流程使用 `POST /v2/blemesh/query_dev`，以既有裝置 `did` 查詢並取回 `gatt_ltmk`。
3. 經既有帳號官方登入後，對本人香氛機執行上述唯讀查詢，取得 32 位元組 Mesh 金鑰；與先前候選金鑰不同。未呼叫 bind、provision_done、金鑰變更或解除配對端點。
4. 僅替換登入探測的金鑰，沿用原有公鑰交換與登入證明計算，實機回覆 `51 00 00 00`。新金鑰的 `verified_on_device` 已設為 true。
5. 登入後以 FE95／001a、001b 的加密 MIoT 屬性通道接收到可解密的真實屬性：`2.2=1`（擴香開啟）、`2.3=4`（4 秒）、`2.4=20`（20 分鐘）、`3.1=0`（燈光關閉）。這是接收當時的狀態，不是永久設定。

裝置會主動送出多個屬性通知，因此不能將「下一個收到的封包」直接對應成剛送出的查詢結果。狀態必須依回覆內的 siid／piid 分類，控制必須另外驗證讀回，不能只採信傳輸 ACK。

新金鑰保存於 Git 忽略的 `.local/diffuser-mesh-key.json`，不輸出到聊天、日誌或前端。登入工具使用完畢已停止。證據：`.local/diffuser-mesh-auth-result.json`、`.local/diffuser-mesh-read-result.json`。後者是初步原始封包紀錄，其 `property_results` 內請求與回覆尚未正確關聯，不可用來宣稱指定屬性讀取已完成。

來源：

- [Telink 官方 SDK：Mesh 登入狀態碼](https://github.com/telink-semi/tc_ble_mesh/blob/master/vc_debug_tool/ble_lt_mesh/vendor/common/mi_api/libs/mesh_auth/mible_mesh_auth.h)
- [小米官方應用商店：米家](https://app.mi.com/details?id=com.xiaomi.smarthome)
- [小米官方 SDK：BLE Spec 屬性 API](https://github.com/MiEcosystem/miot-plugin-sdk/blob/master/miot-sdk/device/bluetooth/blespec.js)

靜態分析用 APK SHA-256：`73335d3c17dff3e73097db7e2f86a373b7eb2c67611dc82749883ab2da3f0b6e`。分析結果僅供本機互通性研究，不隨產品發布官方 APK 或反編譯程式碼。

## 擴香與燈光控制實測成功（2026-10-13 最新）

Windows 電腦已直接透過藍牙控制 `xiaomi.diffuser.xw2iv`，韌體 `2.1.3_3115`。本次沒有小米網關參與，也沒有重置、重新配對或修改韌體。這是研究工具的實機成果，**尚未接入正式 FastAPI 與 Dashboard**。

| 功能 | 本次結果 |
| --- | --- |
| Mesh 管理者登入 | 正確 `gatt_ltmk`，收到 `0x51` 成功回覆 |
| 擴香開關 `2.2` | 開 → 關 → 開，每次以新的同屬性查詢確認 |
| 燈光開關 `3.1` | 關 → 開 → 關，每次以新的同屬性查詢確認 |
| 電池 `5.1` | 新查詢讀回 100% |
| 擴香時間／間隔 | 讀到 4 秒／20 分鐘；寫入仍未驗證 |
| 亮度／色彩／自動功能 | 可收到屬性；寫入仍未驗證 |

測試後已恢復原本「擴香開、燈光關」。證據為 Git 忽略的 `.local/diffuser-state-result.json`；`controls` 的四個結果均 `readback_confirmed=true`，`receive_error=null`。

協定注意事項：

- 開啟屬性通道後持續處理通知，依 siid／piid 歸類。主動查詢使用實測可行的 op2，回覆 op3 必須同時符合交易識別碼與屬性識別碼；op1 查詢在此實機未取得有效回覆。
- 控制 ACK 並不代表狀態已變更。首次立即查詢仍讀到舊值，後續改為有期限的重新查詢，才正確確認控制結果。
- `.local/mesh_session.py` 與相關探測腳本屬研究原型，尚缺正式服務的重連、並行序列化、接收計數器保護與長時間測試，不應直接當作常駐整合上線。
- 封包解析的五項單元測試涵蓋通知分類、會話封包、查詢狀態碼、失敗狀態及截斷封包。實機控制證據與離線測試結果分開保存。

目前已證明這台電腦可在不新增網關的情況下進行基本控制。樹莓派可作為後續移植候選，但其藍牙接收距離、Linux／BlueZ 權限、容器藍牙存取及長時間連線仍須實測，不能把 Windows 成功視為樹莓派已驗證。
> 最新：研究結果已接入正式網頁，並完成出香時長、間隔、亮度及 RGB 顏色的寫入驗證。請見 [香氛機藍牙設定](DIFFUSER_BLUETOOTH.md)；以下保留研究歷程。
