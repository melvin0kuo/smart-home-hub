$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
$vitePath = Join-Path $projectRoot 'frontend/node_modules/vite/bin/vite.js'
if (-not (Test-Path -LiteralPath $pythonPath) -or -not (Test-Path -LiteralPath $vitePath)) { throw '請先執行 scripts/setup.ps1' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) { throw '缺少 .env，請先執行 setup.ps1' }
foreach ($port in @(8000,5173)) { if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "連接埠 $port 已使用；不會停止未知程序。" } }
$localPath = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Path $localPath -Force | Out-Null
$backend = Start-Process -FilePath $pythonPath -ArgumentList '-m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localPath 'backend.log') -RedirectStandardError (Join-Path $localPath 'backend-error.log')
try {
    $frontend = Start-Process -FilePath (Get-Command node).Source -ArgumentList ('"' + $vitePath + '" --host 127.0.0.1') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localPath 'frontend.log') -RedirectStandardError (Join-Path $localPath 'frontend-error.log')
    @(@{id=$backend.Id;started=$backend.StartTime.ToUniversalTime().ToString('o')},@{id=$frontend.Id;started=$frontend.StartTime.ToUniversalTime().ToString('o')}) | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $localPath 'processes.json') -Encoding utf8
    $ready = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($backend.HasExited -or $frontend.HasExited) { throw '服務啟動失敗，請查看 .local 日誌。' }
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; $page = Invoke-WebRequest 'http://127.0.0.1:5173/' -TimeoutSec 2; if ($health -and $page.StatusCode -eq 200) { $ready=$true; break } } catch { }
    }
    if (-not $ready) { throw '服務啟動逾時，請查看 .local 日誌。' }
    Write-Host 'Smart Home Hub 已啟動：http://127.0.0.1:5173'
    Write-Host 'API 文件：http://127.0.0.1:8000/docs'
    Write-Host '帳號：admin；密碼：根目錄 .env 的 HUB_ADMIN_PASSWORD'
} catch {
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    if ($frontend) { Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue }
    throw
}
