# 裝置捷徑與詳情（2026-10-13）

總覽、裝置與插座頁採用同高捷徑，避免進階設定撐高整列。常用開關保留在卡片下方；可操作能力仍依後端驗證結果判斷，沒有新增插座總開關，重要插孔保護保留。除濕機水箱已滿提示仍直接顯示。

點卡片開啟原有 DeviceCard 詳情控制。767 px 以下為全螢幕，平板／電腦為右側面板。原生 dialog 處理焦點限制及 Escape；開啟時鎖定背景捲動，關閉恢復焦點與位置。手機採雙欄，350 px 以下改單欄。攝影機捷徑不載入播放器，詳情沿用原本手動播放與隱私控制。

驗證：18 項前端測試、ESLint、TypeScript、Vite Build 通過。390 px 手機實測詳情填滿視窗，返回後捲動位置維持 508 px；820 px 平板詳情寬 600 px、左側起點 220 px。鍵盤 Escape 返回成功；所有桌面捷徑高度均 270 px。沒有為版面驗證切換真實電器。

仍有既有 Vite 產物大小提示；實體 iPhone／iPad 的觸控與 VoiceOver 尚未實測。截圖保存在 Git 忽略的 `.local/shortcuts-mobile.png`、`.local/shortcuts-tablet.png`、`.local/shortcut-detail-mobile.png`、`.local/shortcut-detail-tablet.png`。
