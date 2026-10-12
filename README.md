# Smart Home Hub

**v0.1.0 · 第一個公開預覽版本**

以繁體中文操作的智慧家庭整合平台：React + TypeScript 前端、FastAPI 後端，透過 Home Assistant 統一管理設備，另提供可選的米家香氛機本機藍牙整合。首頁使用精簡捷徑，手機開啟全螢幕控制，平板與電腦使用右側詳情。

> 沒有設備也能先跑 Mock Mode。Real Mode 必須準備自己的 Home Assistant、帳號、Token 與 Entity 映射。範例資料不代表實機支援；本專案沒有隨附任何帳號、密碼或家庭設定。

## 第一版包含什麼

- 登入、管理員與唯讀角色、同源檢查與 CSRF 保護。
- 裝置列表、房間篩選、快速開關、完整控制詳情、深淺色與響應式介面。
- 統一設備能力與操作 API；未驗證、離線或過期的能力不可操作。
- Home Assistant REST／WebSocket 連線、狀態訂閱及重連。
- 經 HA 提供的燈具、插座、環境感測、部分除濕機控制。
- 攝影機受登入保護的串流代理、隱私開關與已驗證 ONVIF PTZ。
- HA `remote` 實體的白名單紅外線按鍵。
- 可選的米家香氛機 BLE 控制：擴香、燈光、出香時長／間隔、亮度與 RGB。
- SQLite 操作紀錄、Mock 測試資料及模擬情境。

**尚未完成：**香氛機定時、一般化規則編輯器、真實情境編輯器、未取得實機資料的電力統計、溫濕度計 BLE 實測，以及樹莓派／arm64 部署驗證。第一版不是涵蓋所有 Tapo 或小米型號的通用驅動。

## 系統架構

```text
瀏覽器／手機
  → React + TypeScript
  → FastAPI（登入、能力檢查、紀錄、狀態確認）
      ├─ Home Assistant REST / WebSocket → 你已整合的設備
      └─ 可選 BLE Provider → xiaomi.diffuser.xw2iv
```

Home Assistant 是獨立的設備整合服務，本專案是其上方的自製前後端。Home Assistant Token 留在後端；瀏覽器不直接取得品牌帳密或攝影機 RTSP 密碼。

## 1. 先啟動 Mock 測試版

準備 Git、Python 3.12+、Node.js 24 與 npm。Windows 建議 PowerShell 7。發布前實測環境為 Windows、Python 3.14.4、Node 24.15.0；其他平台請依測試結果自行驗證。

```sh
git clone https://github.com/melvin0kuo/smart-home-hub.git
cd smart-home-hub
```

### Windows

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

setup 安裝後端與前端依賴，建立 `.env` 的隨機密碼與 Session 密鑰。既有 `.env` 會保留。若腳本被阻擋，依自己的 PowerShell 執行原則允許此專案；不必永久關閉防護。

- 網頁：[http://127.0.0.1:5173](http://127.0.0.1:5173)
- API 文件：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 帳號：`admin`；密碼：本機 `.env` 的 `HUB_ADMIN_PASSWORD`。
- 停止：`.\scripts\stop.ps1`。一般停止不會刪除資料。

### Linux／macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
.venv/bin/python scripts/init_env.py
```

兩個終端機分別啟動：

```sh
cd backend
../.venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

```sh
cd frontend
npm run dev
```

Windows 的 `.venv` 和 `node_modules` 不能直接複製至 Linux。第一次啟動保留 `HUB_MODE=mock`，確認登入、捷徑及模擬開關正常，再接實機。

## 2. 建立自己的 Home Assistant

Home Assistant 與本平台分別安裝；**不需要把 Home Assistant 安裝進本專案的 Python 虛擬環境。**

### 方式 A：樹莓派安裝 Home Assistant OS

適合常駐使用。依 [Home Assistant 官方樹莓派教學](https://www.home-assistant.io/installation/raspberrypi/) 操作：

1. 準備 Raspberry Pi 4／5、適當電源、32 GB 以上儲存裝置與網路線。
2. 在電腦安裝 Raspberry Pi Imager，選擇對應機型的 Home Assistant OS，確認目標儲存裝置後寫入。**寫入會清除目標裝置資料。**
3. 將儲存裝置放入樹莓派，接到家庭網路後開機。
4. 開啟 `http://homeassistant.local:8123`；若名稱解析失敗，從路由器 DHCP 清單找到樹莓派 IP，改用 `http://<HA-IP>:8123`。
5. 建立自己的 HA 帳號、家庭、時區，先完成備份，再加入設備。

HA OS 是專用系統。第一版建議 HA 放樹莓派，本平台先跑電腦；本專案尚未提供 HA OS App 安裝包。

### 方式 B：Windows 使用 Home Assistant OS 虛擬機

依 [官方 Windows 安裝教學](https://www.home-assistant.io/installation/windows/) 下載相符的 VirtualBox／VMware／Hyper-V 映像。建立虛擬機後確認 UEFI、資源與網路；設備探索需要合適的區域網路連通性。開機後依虛擬機顯示的 IP 開啟 HA，完成帳號設定。

### 方式 C：熟悉 Linux／Docker 的使用者

依 [官方 Home Assistant Container 教學](https://www.home-assistant.io/installation/linux/) 部署。Container 沒有 HA OS 的 Supervisor／Apps；Matter、藍牙及 mDNS 需自行處理網路與硬體存取。完整步驟及 WSL 試用限制見 [Home Assistant 安裝指南](docs/HOME_ASSISTANT_LOCAL.md)。

## 3. 把設備加入 Home Assistant

先在 HA「設定 → 裝置與服務」完成整合，再讓本平台讀取。不要只憑品牌勾選已支援。

| 設備 | 優先路徑 | 第一版限制 |
| --- | --- | --- |
| Tapo P306 | TP-Link Smart Home | 查核各智慧插孔；一般插孔不可遙控，未確認電力監測 |
| Tapo H110 | HA 可用的 `remote`／社群 IR 整合 | 紅外線需既存白名單指令；此 repo 不包含 HA 自訂元件 |
| Tapo C260 | ONVIF／RTSP；隱私另需可用的 HA 開關 | PTZ、隱私語意須逐項驗證；不宣稱所有 AI 事件可用 |
| 米家檯燈 1S | HomeKit Device 或 Xiaomi Home | 已配對 Apple Home 時不可直接假設能再配對；勿任意重置 |
| 米家溫濕度計 | Xiaomi BLE／相容接收器 | 實際型號、Bindkey 與接收穩定性待驗證 |
| 米家智慧香氛機 | 可選後端 BLE | 僅實測 `xiaomi.diffuser.xw2iv`；需合法取得自己的 Mesh 金鑰 |
| Electrolux EDH14TRBD2 | 已配置的 HA Electrolux 社群整合 | 依賴官方雲端、自己的 API 憑證及整合版本 |

詳細流程、來源與驗證界線：[SETUP_GUIDE](docs/SETUP_GUIDE.md)、[相容性矩陣](docs/DEVICE_COMPATIBILITY.md)。

## 4. 讓平台連到 Home Assistant

1. 在 HA 建立平台專用帳號，再於該帳號個人檔案的安全性區建立長期存取權杖。
2. 將 `docs/ha-mapping.example.json` 複製到 `.local/ha-mapping.json`，改成自己的 Entity ID。範本預設唯讀。
3. 編輯 `.env`，保留原本平台隨機密碼：

```dotenv
HUB_MODE=real
HA_URL=http://<你的-HA-IP>:8123
HA_TOKEN=<只在本機填入>
HUB_MAPPING_FILE=<私有映射檔的絕對路徑>
```

`HA_URL` 不包含 `/api` 或密碼。Windows 路徑可使用 `C:/projects/smart-home-hub/.local/ha-mapping.json`；Linux 使用自己的完整路徑。

4. 重新啟動平台，先確認讀值與實機一致。
5. 在 HA 對可安全操作的設備測試後，才將對應能力設成 `verification_status: "verified"`、`writable: true`。路由器、電腦總電源等重要負載建議保留唯讀。

設備命令必須取得狀態確認才顯示成功。逾時可能代表設備已執行但回報未到；先查看實際狀態，避免連續重送。

## 5. 可選：香氛機藍牙

```sh
python -m pip install -r backend/requirements-ble.txt
```

使用執行後端的 Python 安裝。需 Bluetooth Adapter、裝置在接收範圍內，以及自己的 `gatt_ltmk`。私有 JSON 路徑放在 `HUB_BLE_DIFFUSER_CONFIG`；不要填一般 BLE Bindkey 代替 Mesh 金鑰。

詳見 [香氛機整合](docs/DIFFUSER_BLUETOOTH.md)。金鑰擷取研究工具沒有隨 repo 發布，這不是無需設定的一鍵整合。只執行一個後端 worker；手機 App 可能占用同一條藍牙連線。

## 6. Docker、手機與遠端使用

已提供 `docker-compose.yml`，預設為 Mock，容器與 arm64 尚待獨立驗證：

```sh
python3 scripts/init_env.py
docker compose config --quiet
docker compose up --build -d
```

入口 `http://127.0.0.1:8080`；一般停止使用 `docker compose down`，不要加刪除 volume 的選項。Real Mode 必須另外掛載私有 Entity 映射，並使用容器可以連到的 HA URL；容器內的 `127.0.0.1` 是容器本身。預設 Compose 不提供 BLE 存取。

要以手機遠端使用，可採 VPN／Tailscale Serve，保留平台登入與 HTTPS，將自己的完整 Origin 加入 `HUB_ALLOWED_ORIGINS`。範例沒有公開網站或預設帳密，不預設啟用公網 Funnel。詳見 [私人存取](docs/PRIVATE_ACCESS.md)、[樹莓派移植](docs/RASPBERRY_PI.md)。

## 7. 開發與驗證

```sh
# 在 backend 目錄，使用專案的 Python
python -m pytest tests -q
python -m ruff check .

# 在 frontend 目錄
npm test
npm run lint
npm run build
```

發布前本機結果：後端 58 項、前端 18 項通過；Lint、TypeScript 與 Vite Build 通過。Vite 仍有產物大小提示。安裝可選 BLE 依賴後才會執行其工作階段測試。

E2E 僅能對 **Mock** 環境執行，不能拿真實設備當測試開關。CI 驗證原始碼與建置，不等於設備、實體手機或樹莓派測試。

```text
frontend/       React、捷徑與詳情、API 客戶端
backend/app/    FastAPI、權限、設備能力、HA／BLE Provider
backend/tests/  API、異常與確認測試
scripts/        環境建立與本機啟停
docs/          安裝、架構、API 與設備文件
```

## 文件與第一版範圍

- [從零設定設備與映射](docs/SETUP_GUIDE.md)
- [系統架構](docs/ARCHITECTURE.md)／[API 設計](docs/API_DESIGN.md)
- [環境檢查](docs/ENVIRONMENT_CHECK.md)／[開發計畫](docs/DEVELOPMENT_PLAN.md)
- [v0.1.0 更新紀錄](CHANGELOG.md)

`.env`、Token、Bindkey、Mesh 金鑰、SQLite、攝影機網址、HA 備份與實機診斷資料均不應提交。回報問題時請移除帳號、位址與憑證。Home Assistant、Tapo、Xiaomi、Electrolux 等名稱屬各自權利人，本專案為獨立整合平台。
