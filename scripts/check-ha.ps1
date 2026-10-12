$ErrorActionPreference = 'Stop'
# 只從 Windows 驗證服務，不啟動 WSL，避免檢查本身掩蓋閒置停止問題。
$response = Invoke-WebRequest -Uri http://127.0.0.1:8123/ -TimeoutSec 10
if ($response.StatusCode -ne 200 -or $response.Content -notmatch 'Home Assistant') { throw 'HA 網頁未正常回應。' }
$denied = Invoke-WebRequest -Uri http://127.0.0.1:8123/api/states -TimeoutSec 10 -SkipHttpErrorCheck
if ($denied.StatusCode -ne 401) { throw 'HA API 未正確拒絕未授權讀取。' }
Write-Output 'PASS：HA 網頁 200，未授權 API 401。'
