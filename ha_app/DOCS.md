# App 設定

完整安裝與限制見 [README](README.md)。

| 選項 | 用途 |
| --- | --- |
| mode | mock 示範／real 真實 HA，離線不自動回退模擬 |
| admin_password | 自製平台管理員密碼，至少 12 字元 |
| ha_url | App 後端可達的 HA 基底網址 |
| ha_token | 私有 HA 長期權杖，只供後端使用 |
| ha_browser_url | 手機／電腦瀏覽器可達的 HA 配對網址 |
| allowed_origins | 實際使用的自製平台 origin 清單 |
| mapping_json | 可留空；有專屬控制時提供自己的完整私有映射 JSON |

初版不啟用直接藍牙；不設定額外硬體權限，不要求關閉 App 保護模式。映射不正確或設定驗證失敗時，啟動會停止，日誌不回傳秘密欄位。
