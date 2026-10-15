# 從零建立 Home Assistant

Home Assistant 與本平台分開安裝，不需要安裝進 FastAPI 的 Python 虛擬環境。先看 [README](../README.md) 的完整步驟。

## 選擇安裝方式

- 樹莓派常駐：依 [官方樹莓派指南](https://www.home-assistant.io/installation/raspberrypi/) 使用 Raspberry Pi Imager 寫入對應機型的 HA OS。確認目標儲存裝置與備份，寫入會清除該裝置資料。接網路線並開機，使用 homeassistant.local:8123；名稱解析失敗時使用 DHCP 清單中的 HA IP。
- Windows：依 [官方 VM 指南](https://www.home-assistant.io/installation/windows/) 下載 VirtualBox／VMware／Hyper-V 對應映像，配置 UEFI、CPU、記憶體與網路，再使用 VM 顯示的 IP 設定。NAT／網路隔離可能阻止設備探索。
- Linux：依 [官方 Container 指南](https://www.home-assistant.io/installation/linux/) 安裝 Docker、掛載持久 config、配置區域網路，再啟動官方映像。Container 沒有 HA OS Supervisor／Apps，USB、Bluetooth、D-Bus、Matter 與 mDNS 需自行配置。

建立自己的 HA 帳號、家庭、時區與備份後才加入設備。HA OS 是專用系統；v0.1.0 可先讓本平台跑電腦，最新開發版另提供 [HA OS App](../ha_app/README.md)，可讓網頁與後端同機執行。

## 可選 WSL 本機試用

前提是已有 WSL2 發行版與可用 Docker Engine：

    .\scripts\ha-local.ps1 -Action Status -Distro Ubuntu-26.04
    .\scripts\ha-local.ps1 -Action Start -Distro Ubuntu-26.04
    .\scripts\ha-local.ps1 -Action Stop -Distro Ubuntu-26.04

腳本不安裝 WSL／Docker。初次建立使用官方 HA Container 2026.10.1；資料目錄依目前 WSL 使用者決定，可用 -ConfigPath 指定 Linux 絕對路徑。需要已有 Docker 權限，只管理標記為本專案的同名容器。

此試用採 loopback 8123／Docker bridge，入口 http://127.0.0.1:8123，與原生 Linux host 網路不同。多播、Matter、HomeKit 探索受限，Windows 藍牙不會自動進入容器。背景保活不能保證 Windows 睡眠或重開機後仍可用。

## 連接平台

1. HA「設定 → 裝置與服務」加入自己的設備，秘密只輸入 HA。
2. 在 HA 先比對真實狀態，測試可以安全操作的負載。
3. 建立平台專用 HA 使用者，從個人檔案安全性建立長期權杖。
4. 按 [設定指南](SETUP_GUIDE.md) 建立私有 Entity 映射與 .env，切換 Real Mode。

HA 與本平台保留獨立登入。備份含帳號、Token、配對資料，不能提交 Git。更新前先備份，一般停止不刪 config，Container 到 HA OS 的還原仍須依官方流程驗證。
