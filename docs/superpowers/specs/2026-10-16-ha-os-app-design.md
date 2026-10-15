# HA OS App 移植

使用者目標是 HA 與自製平台一起放在 Raspberry Pi 4B／HA OS，電腦不需常駐。HA 設定已還原至樹莓派並驗證原有實體與重要插孔保護。

新增 `ha_app/` 作為可安裝的 App。Docker 多階段建置從已公開、固定 commit 的原始碼封存檔取得前後端，不把私人設定打包。以單一 FastAPI 程序提供 React 建置結果及 API，LAN 8099 埠，保留平台自身登入。初版不使用 Ingress，避免既有絕對 API／WebSocket 路徑衝突。

設定由 `/data/options.json` 讀取：模式、管理員密碼、HA 位址與既有 Token、瀏覽器 HA 位址、允許來源、私有映射 JSON。Session 密鑰及 SQLite 放 `/data` 持久化。私有映射與密鑰寫入權限 0600，不記錄選項或秘密。App 不要求 Supervisor、Docker API 或完整硬體權限。此版不啟用藍牙，Windows 藍牙 Provider 保留到獨立實測後移轉。

通用空白映射可使用新增裝置精靈；既有家庭可由管理員提供私有映射 JSON。不假造 BLE 成功。部署先 Mock，再唯讀 HA 與保護能力驗證，不自動切換實機電源。新 App 建置／安裝成功後才切換使用入口；失敗保留電腦平台。
