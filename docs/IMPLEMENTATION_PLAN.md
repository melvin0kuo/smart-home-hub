# Windows 測試版本實作計畫

> 依 superpowers:executing-plans 在本次工作中自行實作。使用者於 2026-10-11 明確指示直接在本機建立測試版，之後移植樹莓派。

**目標：** 本機可啟動的 React / FastAPI Mock MVP，具有實際 API 往返、權限與未來 HA 接點。
**架構：** 延用 ARCHITECTURE.md 的 Provider 分層及單程序 SQLite；前端同源代理，HA 秘密只在後端。
**技術：** Python 3.12+（本機 3.14 實測）、React / TypeScript / Vite、Tailwind、TanStack Query、SQLAlchemy、pytest。
**規格：** ARCHITECTURE.md、API_DESIGN.md、原始使用者需求。

## 共通限制與審查重點

繁體中文 UI / 文件 / 註解。Mock 成功不提升實機驗證狀態。未知能力無寫入介面。不動設備配對與防火牆。登入與寫入要求驗證；秘密不在前端。Windows 原生啟動，Linux arm64 容器另提供設定而不冒稱樹莓派實測。

特別測試：錯誤 target 不可操作另一孔；離線/未知設備不可寫；來源中斷不可沿用在線快取；HA 接受不等於執行確認；session 撤銷/CSRF/跨站 Origin 不能操作或接收事件。

## 任務 1：設備與安全 API

檔案：backend/app/models/{device,storage}.py、core/{config,security,errors}.py、integrations/{base,mock}.py、services/{devices,events,repository}.py、api/routes.py、main.py、tests/test_api.py。
介面：create_app(settings)->FastAPI；Provider.devices()->list[Device]，Provider.action(id,Action)->Device；POST actions 回傳操作結果。
- [x] 建立測試：未登入 401、六設備與三個智慧 AC、逐孔控制、亮度範圍、unsupported、離線、CSRF、Origin、登出及歷史。
- [x] 執行 pytest，確認尚無實作而失敗。
- [x] 實作型別、SQLite 紀錄/session、Mock Provider、權限及 API。
- [x] pytest 通過並執行 ruff。

## 任務 2：HA Client 與 Real Provider

檔案：integrations/{home_assistant,real}.py、tests/test_home_assistant.py、tests/test_real.py。
介面：HAClient.states()、call_service(domain,service,entity_id)、stream(on_state,on_connection)；RealProvider 僅讀私有映射。
- [x] 測試認證錯誤、逾時、格式異常、WS 認證/訂閱與重連、未驗證能力拒絕、服務接受但狀態未更新。
- [x] 執行失敗測試，實作受控 Client、白名單映射與狀態確認後再跑測試。

## 任務 3：Dashboard

檔案：frontend/src/types、services/api.ts、components/DeviceCard.tsx、pages/Dashboard.tsx、App.tsx、styles.css；tests/ 與 e2e/。
介面：/api 登入與設備；/ws/events 使 Query cache 失效並重抓。
- [x] 先測能力判斷及 API 錯誤處理；再實作登入、總覽、篩選、深淺色、情境與紀錄。
- [x] 測 Mock 完整登入與智慧 AC 操作、待支援設備無按鈕、登出。
- [x] npm test、lint、build；實際瀏覽器檢查桌面/手機。

## 任務 4：交付與移植

檔案：scripts/setup.ps1、start.ps1、stop.ps1、Dockerfile、docker-compose.yml、README、docs 狀態更新。
- [x] 產生本機隨機秘密且不輸出到日誌；啟動服務僅繫結 127.0.0.1。
- [x] 鎖定相依套件；驗證原生啟動、API 文件與瀏覽器流程。
- [x] 提供樹莓派 64 位元 Linux / arm64 移植指令，列明 Docker / 樹莓派尚未實測。

## 決策紀錄

初版控制同步等待結果，Mock 回傳 confirmed；Real 上游接受後等待讀回目標狀態，逾時明確回報，不假裝已成功。這取代原草案 202 非同步操作佇列，減少本機測試版複雜度；紀錄與 WS 仍推送結果。

執行結果：本機測試版已建立並驗證，細節見 VERIFICATION.md。Docker、樹莓派與實體設備不包含在本機通過的範圍內；對應項目仍待目標環境驗證。
