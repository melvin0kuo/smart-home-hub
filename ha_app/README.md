# Smart Home Hub — HA OS App

在 HA OS 上執行自製 React 網頁與 FastAPI，與 Home Assistant 分開登入。初版包含網頁、後端、SQLite 與 HA 連線，尚未包含香氛機直接藍牙 Provider。

2026-10-16：App 0.1.1 已在 Raspberry Pi 4／aarch64 完成原生建置、Real Mode 啟動、登入保護與重啟持久化驗證；未進行實機電源切換。不是全部型號／全部控制功能的驗證。

## 安裝

1. HA「設定 → 應用程式 → 應用程式商店」的儲存庫加入 `https://github.com/melvin0kuo/smart-home-hub`。
2. 安裝 Smart Home Hub。首次在樹莓派原生建置，需要網際網路與一些時間。
3. 在 App 設定填入至少 12 字元的 `admin_password`。這是自製平台的密碼，不是 HA 密碼。
4. 保留 `mode: mock` 先啟動，以 `admin` 帳號確認網頁。
5. 切換 Real 前填入自己的 `ha_url`、既有 HA 長期權杖 `ha_token`、手機可達的 `ha_browser_url`。
6. `allowed_origins` 加入實際開啟平台的網址，例如自己的 `http://樹莓派IP:8099`。不含路徑、帳密或 Token。
7. 通用設備可使用網頁新增精靈；既有專屬功能可在 `mapping_json` 填入私有映射 JSON。不可使用示範未驗證映射假裝已支援。
8. 重啟 App，開啟 `http://樹莓派IP:8099/`，核對狀態與重要電源保護，再啟用開機自動啟動。

設定中的 `ha_url` 是 App 容器可達的 HA 位址，預設 `http://homeassistant:8123`；`ha_browser_url` 是手機可達的 HA 網址。App 不代理 HA 登入，也不要求 Supervisor／Docker API 管理權限。

## 資料與限制

SQLite、Session 密鑰及私有映射保存於 App `/data`，需要將本 App 納入 HA 備份。不要將 HA Token 或私有 mapping_json 貼到 GitHub。設定頁面僅 HA 管理員應可存取。

本版初次安裝建立自己的 SQLite；電腦的操作歷史與匯入資料庫不會自動搬移，請先保留電腦資料庫備份。專屬映射可透過 mapping_json 移植，通用匯入可重新選取實體。停止電腦後端前確認其是否仍負責香氛機藍牙，這部分尚待 Linux／BlueZ 實測。

LAN 8099 為平台入口，需要平台登入。此版不提供 Ingress；不預設公開到網際網路。遠端連線使用私人 VPN，樹莓派 VPN 帳號授權需要使用者自行完成。

Dockerfile 固定使用公開原始碼 commit `42d80195ab751a0ab25b3bc53d2900c533966008`，不複製本機 `.env`、資料庫、Windows venv 或 node_modules。後續升級需更新固定版本並回歸測試。
