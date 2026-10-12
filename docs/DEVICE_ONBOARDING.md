# 通用裝置新增：探索、配對、匯入

2026-10-13 開發版功能。使用目前 HA 的整合目錄，不以開發者持有的型號作為品牌白名單。

## 使用流程

1. 管理員按「新增裝置」，預設進入「探索與配對」。
2. 查看「HA 已探索，等待設定」。重新探索只重新讀取 HA 結果，不執行全網路掃描。若沒有結果，可直接搜尋品牌英文名稱、別名或協定。
3. 搜尋品牌或選「常見協定」，查看準備條件及指引。目錄含目前 HA 可設定的整合與已安裝社群整合；不是完整產品型號清單，也不保證所有功能可用。
4. 按「在 HA 開始設定」於獨立分頁開啟 HA 流程。HA 可能先要求登入及確認新增，依指示完成。已探索設備請在 HA「已發現」卡片按設定，不要重複新增相同流程。
5. 返回平台按「配對完成，讀取設備」，進入「已連線設備」並重新取得候選。只有候選實際出現才可匯入；點連結或按完成不代表配對成功。
6. 按 [實體匯入指南](DEVICE_IMPORT.md) 設定名稱、房間及操作保護。

可切換「已連線設備」直接匯入既有 HA 實體。品牌／配對失敗不阻止既有控制或匯入。Mock 目錄只示範指引，不提供真實配對連結。

## HA 連線與手機

`HA_URL` 是後端連線位址；`HA_BROWSER_URL` 是使用者瀏覽器開啟 HA 配對頁的位址。留空沿用 `HA_URL`。

後端與 HA 同主機時 HA_URL 可以使用本機位址，但手機需要區域網路或私人 VPN 可達位址。HA_BROWSER_URL 必須是 HTTP(S) 基底網址，不含 `/api`、帳密、Token、查詢參數或片段。修改後重新啟動後端。

```dotenv
HA_URL=http://127.0.0.1:8123
HA_BROWSER_URL=http://homeassistant.local:8123
```

上例名稱需由手機實際解析且可達。Docker 後端內的 localhost 指向容器本身，請依部署拓樸設定 HA_URL。本功能不會自動公開 HA 或設定 Tailscale／防火牆，也不代理 HA Token 到瀏覽器。

目錄與探索使用 HA 管理功能；HA Token 對應使用者需有相應管理員權限。本平台仍要求管理員 Session。權限不足或 API 不相容會個別顯示錯誤，不自動擴權；既有控制仍可保留原 Token。

## 資料來源

- HA 動態目錄：整合名稱與品牌別名，直接讀取本地 HA，不下載執行第三方驅動。
- [Zigbee2MQTT 裝置庫](https://www.zigbee2mqtt.io/supported-devices/)：型號與能力；實際通訊需 Zigbee2MQTT、協調器與 MQTT。
- [CSA 認證產品庫](https://csa-iot.org/csa-iot_products/)：Matter／Zigbee 認證；不代表所有功能已由 HA 或本平台支援。
- [ESPHome 裝置庫](https://devices.esphome.io/)：設定範本與指南；不自動刷韌體。

後三者目前提供查詢連結，尚未同步全量資料或實作型號自動比對。

## 技術與相容性

唯讀查詢：`GET /api/config/config_entries/flow_handlers`、WebSocket `integration/descriptions` 與 `config_entries/flow/progress`。已對 Home Assistant Core 2026.10.1 實際唯讀驗證。這些是 HA 前端介面，並非跨版本穩定合約；升級需回歸測試。名稱讀取失敗時用整合代碼；探索失敗仍可用目錄；目錄失敗只顯示不可配對的參考指引，仍可切回匯入。

API 只投影整合代碼、名稱、別名與探索來源，不傳出 flow context、title_placeholders、帳密、原始設備 URL 或 Token。不執行新增、取消、重置、解除配對或實機控制；登入／OAuth 由 HA 及品牌官方頁面完成。

來源：[HA Config Entries](https://github.com/home-assistant/core/blob/2026.10.1/homeassistant/components/config/config_entries.py)、[HA WebSocket Commands](https://github.com/home-assistant/core/blob/2026.10.1/homeassistant/components/websocket_api/commands.py)、[HA 前端新增入口](https://github.com/home-assistant/frontend/blob/dev/src/panels/config/integrations/ha-config-integrations-dashboard.ts)。
