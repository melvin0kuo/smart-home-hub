# 通用裝置新增 Implementation Plan

**Goal:** 提供基於 HA 動態目錄與探索結果的一站式新增入口。
**Architecture:** 唯讀 HA 查詢 → 安全投影 onboarding API → 搜尋與操作指引 → HA 官方配對 → 既有匯入精靈。
**Tech Stack:** FastAPI、HTTPX、WebSocket、React、TypeScript。
**Spec:** ../specs/2026-10-13-device-onboarding-design.md

## Constraints
- 不變更實機配對、電源、網路及韌體；不輸出秘密。
- 使用者已要求直接製作，採本工作階段直接執行，不額外停下要求設計確認。
- HA 前端 API 非跨版本穩定合約，需記載來源、降級與驗證版本。

## Tasks
- [x] 測試動態目錄、無效輸入過濾、探索秘密剝除、部分失敗及管理員限制，觀察失敗。
- [x] 實作 HA 唯讀查詢與 onboarding API、網址檢查、常見協定指引。
- [x] 測試前端搜尋、模式切換文案、Mock 與配對網址行為，觀察失敗。
- [x] 實作探索／搜尋／指引頁並接上既有精靈，保留選取及保護流程。
- [x] 執行後端、前端測試與 lint/build，瀏覽器驗證，唯讀實機查詢。
- [x] 更新 README／設定說明與 API 文件，審查變更，重啟本機並確認既有設備不變。

## 執行紀錄

- 採直接執行；先觀察新增模組／UI 測試失敗，再實作通過。
- Fresh-context 審查提出兩項 P2：探索來源漏列、探索配對後缺少讀取入口；新增失敗回歸測試後修正。
- 後端 94 項及前端 28 項測試通過，Ruff、ESLint、TypeScript／Vite Build 通過。Build 仍有既有大型 bundle 提示。
- 隔離 Mock 瀏覽器完成搜尋、指引、返回讀取及唯讀匯入；正式頁實際取得 938 整合、0 待設定探索項目。原有 6 台設備及保護插孔不變。
- CUA viewport override 未反映於頁面尺寸，未將此當作手機／平板視覺驗證成功；響應式單雙欄規則已加入，仍需實際行動裝置驗證。
- HA_BROWSER_URL 目前沿用 localhost，手機配對需設定可達 HA 網址，不為此自動變更網路公開範圍。
