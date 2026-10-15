# 樹莓派移植

v0.1.0 未完成樹莓派／arm64 實測。建議 HA OS 放樹莓派，本平台先留電腦，按 [HA 指南](HOME_ASSISTANT_LOCAL.md) 與 [設定指南](SETUP_GUIDE.md) 連線。

同一台 HA OS 現在可使用開發版 [Smart Home Hub App](../ha_app/README.md)，提供自製網頁與 FastAPI。一般 Docker Compose 仍不適用於 HA OS。此 App 尚待樹莓派實機部署驗證，未包含直接 BLE 與電腦歷史資料庫自動移轉。

重新建立 venv、依賴與 npm ci，不複製 Windows venv／node_modules。以私有通道移轉設定，調整 URL／路徑，重新查核 Entity 與重要電源保護。BLE 另測 Linux／BlueZ、距離、權限及容器 D-Bus，只跑一個 worker。

驗證順序：Mock → HA 唯讀 → 非重要負載 → 攝影機 → BLE → 重開機／斷線／備份還原。完成後才宣稱該部署支援。
