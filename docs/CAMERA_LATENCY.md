# C260 串流延遲修正

日期：2026-10-12。

## 原因與證據

使用者反映私人頁面影像緩慢。檢查發現播放器設為 lowLatencyMode=false，沒有利用 HA 已產生的低延遲部分片段；後端也未轉送 LL-HLS 播放清單的 blocking reload 參數。當時實機播放清單的完整片段約 11.977／14.032 秒、TARGETDURATION=18，而 PART-TARGET=1 秒。完整片段較長會放大等待與播放落後，不能只用調低影片畫質解釋。

當時 master／media playlist 在本機 API 約 0.007／0.005 秒回應，未顯示本機播放清單代理本身耗時數十秒。這是單次暖串流數據，不代表遠端手機所有資產都能達到同樣速度。舊播放器取樣 readyState=2、bufferedEnd-currentTime 約 0.13 秒，顯示當時接近緩衝耗盡；沒有可靠的舊版現場總延遲秒數，不提供虛構的改善百分比。

來源：[HA Stream／LL-HLS](https://www.home-assistant.io/integrations/stream/)、本機 HA 2026.10.1 stream/hls.py 與 hls.js 已安裝版本型別／設定檢查。

## 修改

- 啟用 Hls.js lowLatencyMode。
- liveSyncDuration=2 秒、liveMaxLatencyDuration=6 秒，超出時由播放器追上；maxLiveSyncPlaybackRate=1.2。
- 限制前向與歷史緩衝，降低累積落後；新增「回到直播」供使用者主動追上。
- 顯示距串流最新位置的估計秒數；這不是以現場鐘面測得的攝影機到螢幕端到端延遲。
- 後端只在 playlist.m3u8 接受數字 `_HLS_msn`／`_HLS_part`，拒絕重複、負值、未知參數及 part 缺少 msn；轉送至既有固定 HA 串流路徑，不允許指定任意上游 URL。
- 部分片段與 preload hint 沿用已登入的本地資產 URL；維持秘密保護、隱私檢查、資產大小與並行限制。
- 緩衝等待重新顯示提示，隱私模式設定未改變。

## 驗證

- 新增 blocking reload 參數轉送／拒絕測試、PART／PRELOAD-HINT URL 重寫測試。
- 前端以實際 Hls 建構子確認低延遲設定合法。
- 後端 pytest：36 通過；前端 Vitest：6 通過；Ruff、ESLint、TypeScript、Vite Build 通過。
- 已部署並在私人 Tailscale HTTPS 頁面實際播放，後端持續收到 `_HLS_msn`／`_HLS_part` 與部分片段請求且回應 200。
- 穩定播放取樣：currentTime=89.017、bufferedEnd=90.477、readyState=4、paused=false、MediaError=null；頁面估計落後約 1.9 秒。

手機端網路、Tailscale 是否走中繼、Wi-Fi 品質及攝影機本身處理仍可能增加總延遲。若修正後仍不滿足 PTZ 操作體感，再獨立評估帶權限保護的 WebRTC／go2rtc 路線，不將新服務公開到外網。本輪沒有部署新串流服務或修改攝影機配對／韌體。
