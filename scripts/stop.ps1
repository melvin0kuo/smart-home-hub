$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot '.local/processes.json'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host '沒有本專案的啟動紀錄。'; exit }
foreach ($entry in (Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json)) {
    $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
    if ($process -and ($process.StartTime.ToUniversalTime().Ticks -eq ([datetimeoffset]$entry.started).UtcDateTime.Ticks)) { Stop-Process -Id $process.Id; if (-not $process.WaitForExit(5000)) { throw '本專案程序尚未結束，請稍後再啟動。' }; Write-Host "已停止本次啟動的程序 $($process.Id)" }
}
