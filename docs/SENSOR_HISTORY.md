# 環境歷史紀錄

具有 `temperature_sensor` 或 `humidity_sensor` 能力的裝置，詳細頁提供 24 小時、7 天、30 天圖表。防潮箱資料獨立呈現，不會取代家庭環境來源。

## 儲存與同步

- 平台使用既有 SQLite 資料庫；HA OS App 路徑為 `/data/hub.db`，新增 `sensor_measurements` 與 `sensor_history_cursors`，更新 App 不會清空資料。
- Real Mode 從已映射的 HA 實體採集，保留各實體自己的事件時間。每分鐘同步一次；首次按日分批補入最近 30 天 HA **實際仍保留**的詳細紀錄，無法補回已清除或加入 HA 前的米家紀錄。
- 歷史游標持久保存，重啟後繼續，重疊區間以主鍵去重。HA 離線或未知數值保存為缺口，同步失敗稍後重試，不影響裝置控制。
- Mock 與 Real 紀錄分開，模擬模式明確標示；沒有預先生成的假歷史。
- 不自動刪除本機量測。128GB 容量可容納大量環境資料，但需持續留意剩餘空間、備份與 SD 卡健康狀態。HA 自身 Recorder 的保留政策不因此改變。
- 查詢在 SQL 依時間區間平均，最多約 1,500 點／曲線；最低最高與筆數從原始數值計算。圖表不跨越斷線或超過 30 分鐘（長範圍依桶寬放大）的稀疏區段連線。

## API

`GET /api/devices/{id}/history?hours=24`：需要平台登入，範圍 1–720 小時。只接受已登錄裝置 ID，不能指定任意 HA entity。回傳 `series`、`summary`、`bucket_seconds`、`range_end`、`sync_failed`、儲存與模式資訊。

## 備份與限制

請在 HA OS 建立包含 Smart Home Hub App 的備份並下載保存。只備份 HA Core 不包含 App 的 `/data/hub.db`。

已存入平台的資料不會因 HA 詳細歷史清除而消失；但若平台停機超過 HA 的詳細歷史保留期，中間已清除的資料無法補回。稀疏狀態變化紀錄不代表固定頻率取樣，也不能保證設備螢幕與廣播封包完全同步。
