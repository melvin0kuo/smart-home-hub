# 裝置匯入精靈 Implementation Plan

> **For agentic workers:** 使用 superpowers:executing-plans 逐項實作，由主代理直接執行。

**Goal:** 從已連線的 HA 於網頁安全匯入設備。

**Architecture:** 獨立 ImportService 進行候選推導、測試及映射持久化；既有 Provider 負責即時狀態與控制。React 獨立精靈元件串接管理員 API。

**Tech Stack:** FastAPI、Pydantic、SQLAlchemy SQLite、React、TypeScript。

**Spec:** ../specs/2026-10-13-device-import-design.md

## Global Constraints

- 繁體中文 UI／文件；憑證不送前端；不新增 AI 協作者或提交署名。
- 原有映射不改動；受保護及已映射實體不可測試；真實環境驗證只讀。
- 開關需明確測試雙向、新狀態確認及十分鐘有效期才可開放。

## Review Focus

- 重複 Entity 及同時匯入：批次交易與唯一鍵防護。
- HA 離線或格式錯誤：清楚錯誤，禁止控制。
- 已達目標但沒有新回報：不能當測試成功。
- 儲存失敗：不得在記憶體留下一半設備。
- 前端跳步／偽造能力：後端重新推導、檢查測試證明。

### Task 1: 匯入服務與持久化

Files: backend/app/services/imports.py、backend/app/models/storage.py、backend/app/services/repository.py、backend/app/integrations/real.py、backend/app/core/config.py；Test: backend/tests/test_imports.py。

Interfaces: ImportService.discover()、test_switch(entity_id, action)、import_devices(items)；Repository.imports()、save_imports(records)。

- [x] 建立並執行失敗測試：能力白名單、秘密過濾、重複、雙向測試、唯讀／保護、逾時、離線、原子儲存與重啟。
- [x] 實作服務及 SQLite 唯一記錄，Real Provider 可從空映射啟動。
- [x] 執行 pytest tests/test_imports.py，預期全部通過。

### Task 2: API 與介面

Files: backend/app/api/imports.py、backend/app/main.py、frontend/src/components/DeviceImportWizard.tsx、frontend/src/services/api.ts、frontend/src/pages/Dashboard.tsx、frontend/src/imports.css。

Interfaces: GET /api/integrations/home-assistant/candidates；POST /api/integrations/home-assistant/test；POST /api/integrations/home-assistant/import。

- [x] 測試未授權、Viewer、CSRF、非法參數及 Mock 完整流程，先觀察失敗。
- [x] 實作 API 與三步驟響應式精靈，新增入口，完成後刷新設備。
- [x] 前端測試候選篩選、測試／保護條件及靜態介面，API 測試全部通過。

### Task 3: 驗證與交付

- [x] 執行後端 pytest／Ruff，前端 Vitest／ESLint／Build。
- [x] 真實 HA 唯讀探索並在手機及桌面檢查精靈，保留現有設備。
- [x] 更新使用指南與已知限制；部署到現有私人測試服務。
