$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv; if ($LASTEXITCODE) { throw 'venv 建立失敗' } }
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
if ($LASTEXITCODE) { throw '後端相依安裝失敗' }
npm ci --prefix frontend
if ($LASTEXITCODE) { throw '前端相依安裝失敗' }
& ./.venv/Scripts/python.exe scripts/init_env.py
if ($LASTEXITCODE) { throw '環境設定失敗' }
Write-Host '設定完成。以 ./scripts/start.ps1 啟動；登入密碼請查看根目錄 .env。'
