# 伊萊克斯 EDH14TRBD2 整合可行性

研究日期：2026-10-13。狀態：實機官方 API、HA 整合、電源／模式／目標濕度寫入及平台數據已驗證。下方唯讀階段為先前進度，最新結果見「控制與家庭環境更新」。

## 使用者實機資訊與目前進度

- 實際型號：EDH14TRBD2。原先提供的「12L 極適家居500」名稱已由此型號取代；官方手冊將 EDH14TRBD2 列在 14L 機型。
- 使用者確認：可透過 Electrolux App 控制；沒有紅外線遙控器。App 精確名稱、帳號地區及韌體仍待確認。
- 官方台灣手冊提供 Wi-Fi／App 說明，使用者亦已確認實機可用；既有配對保留，不重置或重新配對。
- 已以後端 Token 唯讀查詢現有 HA：API 可連線，未找到名稱／Entity ID 含 Electrolux、伊萊克斯或 EDH14 的實體。
- 使用者已將 API Key、Access Token、Refresh Token 保存至本機私有設定。官方 API 的設備清單、info、state 均回應 HTTP 200，找到一台 connected 的 DH 設備，info 確認 EDH14TRBD2。
- 已備份 HA 並安裝 TTLucian/ha-electrolux 3.8.2，固定原始碼 commit `7c3fe4feae83f8e702a737b0f822669c2024415e`。HA 設定流程成功，雲端 API 與即時事件串流均在線。
- 面板軟體 V3.4；網路模組 V3.0.0 Argo（各自為 API／HA 回報欄位，非推測整機韌體版本）。
- 自製頁面新增除濕機卡片，顯示溫度、濕度及滿水警示。已讀到約 24°C、41–44% RH 及滿水 Yes；數值隨即時回報更新。
- 未發送開關、模式、目標濕度、韌體、重置或配對指令。未驗證操作不顯示控制按鈕。


## 選定的驗證路徑

官方 App 既有設備 → Electrolux 官方開發者 API → HA 社群整合候選 → 平台私有映射。

TTLucian/ha-electrolux 的維護者說明列出 APAC／Electrolux Life 與 DH／Husky 除濕機，但未找到 EDH14TRBD2 已驗證的直接證據。品牌、區域及設備類別支援不等於此型號一定支援。使用官方入口 https://developer.electrolux.one/，以 App 同帳號登入，先確認設備清單與 capabilities，再決定是否安裝整合。

此候選路徑依賴雲端，目前沒有確認可維護的本地 API。需要 API Key、Access Token、Refresh Token；秘密只保留於本機後端或 HA，使用者不需貼在聊天中。建立新權限或接受條款時，由使用者在官方頁面確認。

唯讀成功後，依實際回報驗證電源、目前濕度、目標濕度、模式、風速及滿水／濾網資訊；未提供的項目保留待支援，不用推測值填補。首次控制只測試已明確驗證的單一能力，不使用切電替代原生開關。

## 此前泛稱機型的研究紀錄（不適用於推定本機能力）

## 已查證的資料

- 台灣官方有 ED1251DC、ED1251DD 等使用「12L 極適家居500」名稱的產品；不同機型不能共用連線能力假設。
- ED1251DD 官方列出的紅外線感測器規格為 PM2.5、PM10。因此紅外線感測器不能當作紅外線遙控接收器的證據。
- TTLucian/ha-electrolux 社群專案列出 DH／Husky 除濕機類別，其已驗證例子為 Frigidaire 機型；未找到這兩款台灣型號已驗證的證據。
- 該專案使用官方 Electrolux Developer Portal 的 API Key、Access Token、Refresh Token，要求家電先加入官方 App 並可連上網際網路。這是雲端候選路徑，不能標示為本地控制。
- 官方 ED1251DC 路徑的 PDF 搜尋索引出現 Wi-Fi／App 章節，但完整文件尚未解析，不能據此判定該型號一定具備 Wi-Fi；可能為共用手冊，需檢查適用型號限制。

## 待取得資料

1. 完整型號已確認 EDH14TRBD2；不需要序號。
2. 官方 App 可操作已確認；待確認 App 精確名稱、帳號地區。
3. 使用者確認無紅外線遙控器；不採 H110 路徑。
4. 若已有連網：內網 IP、韌體版本與官方 App 回報的可用功能。

## 依能力選擇路徑

| 路徑 | 條件 | 可望提供的功能 | 目前狀態 |
| --- | --- | --- | --- |
| 官方雲端 API → HA 社群整合 | 實機支援官方 App，且開發者 API 能列出該設備 | 依實際 capabilities 決定開關、濕度、模式、風速、滿水提示 | 待驗證；不保證台灣帳號／型號可用 |
| H110 紅外線 | 實機確認有遙控接收器，且有可靠的對應指令 | 僅已驗證按鍵；狀態通常無回報 | 待驗證；不得僅因產品標示感測器而啟用 |
| 智慧插座 | 原廠允許此用途、額定負載與啟動電流相容，且確認復電行為 | 供電控制；不能假裝取得機器運轉、滿水、濕度或模式 | 替代方案，未進行切電測試 |
| 只有面板操作 | 無可用連線與遙控方式 | 可保留設備紀錄，無遠端控制能力 | 待確認 |

優先驗證原生設備介面。智慧插座不能取代原廠的控制及保護機制；不得使用已鎖定的路由器插孔 2 或電腦插孔 3，也不以快速反覆斷電測試壓縮機。

## 接入平台的驗收順序

先確認實際型號及連線 → 以唯讀方式確認官方 API／HA 可用實體 → 建立私有映射 → 僅開放實測成功的能力。濕度、模式或滿水資訊未取得前不顯示虛構數值。帳號授權只使用官方登入流程，秘密保存在後端／HA，不放前端。

## 來源

- [ED1251DC 官方產品頁](https://www.electrolux.com.tw/appliances/dehumidifier/ed1251dc/)
- [ED1251DD 官方產品頁](https://www.electrolux.com.tw/appliances/dehumidifier/ed1251dd/)
- [官方使用手冊搜尋](https://www.electrolux.com.tw/search/product-manual-search/)
- [官方 ED1251DC 路徑的使用手冊](https://www.electrolux.com.tw/globalassets/appliances/dehumidifier/ed1251dc/um-ed1251dc-tw.pdf)
- [ha-electrolux 社群專案與支援清單](https://github.com/TTLucian/ha-electrolux)

- [EDH14TRBD2 台灣官方使用手冊](https://www.electrolux.com.tw/globalassets/appliances/dehumidifier/edh12trbd2-edh14trbd2-edh14trbw2-.pdf)
- [官方開發者入門指南](https://developer.electrolux.one/documentation/gettingStarted)

## 官方 API 唯讀驗證準備

已核對官方參考頁（2026-10-13）：HTTPS 基底為 https://api.developer.electrolux.one，以 x-api-key 及 Authorization: Bearer 標頭授權。取得有效憑證後依序呼叫 GET /api/v1/appliances、GET /api/v1/appliances/{applianceId}/info、GET /api/v1/appliances/{applianceId}/state。保留完整回應於本機私有診斷檔，不輸出序號、SSID 或 Token；以實際 info.capabilities 判定能力。此階段不呼叫 PUT command、不更新韌體或修改配對。

官方授權文件說明 Token 僅供單一應用程式，刷新時會輪替 access／refresh token。後續若以 HA 整合持有刷新權，其他測試工具不得同時刷新同一組憑證，以免失效。

## 實機能力與驗證界線

| 項目 | 官方 API／HA 狀況 | 平台狀態 |
| --- | --- | --- |
| 電源狀態、溫度、濕度、滿水 | 已讀取實機數據 | 已接入，只讀 |
| 電源開關 | API 公開 ON／OFF，HA 有 switch | 寫入待實測 |
| 目標濕度 | API 列出 30–85%，間距 5%；只在 COMPLETE + MANUAL 可調 | 待實測，不用 0–100 的泛用範圍替代列舉限制 |
| 模式、風速、擺葉、面板燈、童鎖 | API 公開能力，HA 已建立對應實體 | 待實測，不開放控制 |
| PM2.5、空氣品質、濾網 | HA 有回報 | 尚未納入平台，感測準確度待確認 |
| 本地離線控制 | 未確認可維護介面 | 不支援宣稱 |

HA 現在負責 Token 刷新；其他程式不得使用同一 Refresh Token 刷新。原始診斷檔與憑證只在 `.local/` 和 HA 私有設定，已由 Git 忽略。重建時需自行安裝上述社群整合並經本機方式提供憑證，不複製秘密至文件或前端。網際網路或官方服務中斷時，資料須顯示不可用。

下一步：先檢查水箱，再挑選單一能力進行實機操作與狀態回報驗證；保持壓縮機保護間隔，確認成功後才開放該控制。


## 控制與家庭環境更新

使用者確認加入電源、模式、目標濕度控制及首頁環境來源。平台沿用 HA API，秘密不傳到前端；每次指令必須收到新狀態回報才算確認。

- 工作模式：完整、連續除濕、衣物乾燥、空氣清淨；運轉方式：自動、手動、安靜。選項來自實機能力與 HA select 實體。
- 目標濕度採 API 與 HA 的交集：35–85%，間距 5%。完整＋手動且電源開啟時才能調整；前後端均檢查。
- 家庭總覽以除濕機的溫濕度為環境來源，顯示來源名稱；此數據代表除濕機所在位置。斷線時不沿用舊值，也不自動換成其他位置的感測器。
- 滿水維持醒目提醒；電源 on 只表示設備已啟用，不代表壓縮機正在除濕。
- 模式與目標濕度測試後還原 Complete／Automatic／50%；關機測試成功後，保留至少三分鐘保護間隔再還原開機。實測記錄只保存在本機。
- 風速、擺葉、童鎖、面板燈與濾網重置未納入這次控制；不宣稱已實測。


### 原廠用語與風速補充

依原廠手冊頁6、8–10修正：COMPLETE＝雙效、DRY＝乾衣、PURIFY＝清淨；AUTOMATIC 對應智慧自動運轉，QUIET 對應睡眠。CONTINUOUS 顯示「除濕（連續）」並保留連續語意，不假裝是可設定目標濕度的另一模式。

實機已完成 Manual → Middle → High → Low 的風速回報驗證，並還原原本運轉模式。Dry、Continuous、Complete、Quiet、Automatic 亦收到實機狀態回報。API 的 fanSpeedSetting 只有 HIGH／MIDDLE／LOW，HA 額外顯示的 Auto 為智慧運轉狀態，平台不把 Auto 當成風速寫入值。手動時才能選擇風速；乾衣時不允許切換運轉模式。手冊對乾衣調風速的說明與 API 的手動條件有差異，平台先遵守 API 宣告，其他組合待獨立實測，不繞過限制。

風向、負離子／cleanAirMode、童鎖、定時、顯示燈仍未納入本次介面。這些 API 欄位不能僅憑英文名稱推定 App 中的完整語意。


### 最終驗收結果

後端40項、前端11項測試通過，Ruff、ESLint及TypeScript／Vite建置通過。透過自製頁面及平台API完成手動模式、55%／50%目標濕度、中／低風速的端到端實機確認；最後讀取確認為開機、Complete、Automatic、50%。390px手機版無水平溢出，1024px平板版可顯示四組設定及環境來源。

實測曾發生10秒內未收到濕度回報而回傳504，稍後官方狀態才出現目標值。除濕機改採30秒確認窗口，仍須新狀態事件，未收到時保留逾時記錄；這不保證雲端永遠即時。重測55%→50%及模式還原均收到200 confirmed。請以最後設備回報為準，避免因逾時連續重送。


### 上下風向控制

已加入「上下自動擺風」開關，對應 `switch.gao_ji_chu_shi_ji_vertical_swing`。沿用 switch 能力、target `swing` 及 turn_on／turn_off API，不切換主電源。已測試 HA on／off 並收到新狀態回報；平台頁面亦可顯示目前狀態及已確認操作紀錄。未知／斷線狀態禁止操作。這是上下擺風開關，沒有宣稱任意角度或左右風向控制。後端41項、前端12項測試及Lint／Build通過。
