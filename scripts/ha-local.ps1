param(
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Status',
    [string]$Distro = 'Ubuntu-26.04',
    [string]$ConfigPath = ''
)
$ErrorActionPreference = 'Stop'
$container = 'smart-home-hub-ha'
$image = 'docker.io/homeassistant/home-assistant:2026.10.1'
if (-not $ConfigPath) {
    $linuxUserHome = (& wsl -d $Distro -- printenv HOME).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxUserHome.StartsWith('/')) { throw '無法取得 WSL 使用者目錄。' }
    $ConfigPath = "$linuxUserHome/smart-home-hub-ha/config"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$localDir = Join-Path $projectRoot '.local'
$keepAliveFile = Join-Path $localDir 'ha-wsl-process.json'
function Get-OwnedKeepAlive {
    if (-not (Test-Path -LiteralPath $keepAliveFile)) { return $null }
    $record = Get-Content -LiteralPath $keepAliveFile -Raw | ConvertFrom-Json
    $ownedProcess = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if ($ownedProcess -and $ownedProcess.ProcessName -eq 'wsl' -and $ownedProcess.StartTime.ToUniversalTime().Ticks -eq ([datetimeoffset]$record.started).UtcDateTime.Ticks) { return $ownedProcess }
    return $null
}

# systemd 服務不會阻止 WSL 閒置結束，保留明確的背景命令讓 HA 持續可用。
if ($Action -eq 'Start' -and -not (Get-OwnedKeepAlive)) {
    New-Item -ItemType Directory -Path $localDir -Force | Out-Null
    $keepAlive = Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d', $distro, '--exec', 'sleep', 'infinity') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localDir 'ha-wsl.stdout.log') -RedirectStandardError (Join-Path $localDir 'ha-wsl.stderr.log')
    @{id=$keepAlive.Id;started=$keepAlive.StartTime.ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $keepAliveFile -Encoding utf8
}

# 此腳本只管理本專案建立的容器，不變更其他 Docker 服務。
& wsl -d $distro -- docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'WSL Docker 無法使用。請先確認 Ubuntu 與 Docker 服務。' }
$owner = & wsl -d $distro -- docker inspect --format '{{index .Config.Labels "com.smart-home-hub.owner"}}' $container 2>$null
$exists = $LASTEXITCODE -eq 0
if ($exists -and $owner.Trim() -ne 'local-trial') { throw '同名容器不是本專案管理的容器，已停止操作。' }

switch ($Action) {
    'Start' {
        if ($exists) {
            & wsl -d $distro -- docker start $container
            if ($LASTEXITCODE -ne 0) { throw 'Home Assistant 啟動失敗。' }
        } else {
            & wsl -d $distro -- mkdir -p $configPath
            if ($LASTEXITCODE -ne 0) { throw '無法建立 Home Assistant 資料目錄。' }
            & wsl -d $distro -- docker run -d --name $container --label com.smart-home-hub.owner=local-trial --restart unless-stopped --stop-timeout 60 --memory 4g --cpus 2 -e TZ=Asia/Taipei -v "${configPath}:/config" -p 127.0.0.1:8123:8123 $image
            if ($LASTEXITCODE -ne 0) { throw 'Home Assistant 容器建立失敗。' }
        }
        Write-Host 'Home Assistant 正在啟動：http://127.0.0.1:8123（首次啟動請稍候）'
    }
    'Stop' {
        if ($exists) {
            & wsl -d $distro -- docker stop --time 60 $container
            if ($LASTEXITCODE -ne 0) { throw 'Home Assistant 停止失敗。' }
        } else { Write-Host '尚未建立 Home Assistant 容器。' }
        $ownedKeepAlive = Get-OwnedKeepAlive
        if ($ownedKeepAlive) { Stop-Process -Id $ownedKeepAlive.Id }
    }
    'Status' {
        if ($exists) {
            & wsl -d $distro -- docker inspect --format '狀態={{.State.Status}} 映像={{.Config.Image}} 網路={{.HostConfig.NetworkMode}} 連接埠={{json .NetworkSettings.Ports}}' $container
            if ($LASTEXITCODE -ne 0) { throw '無法讀取容器狀態。' }
        } else { Write-Host '尚未建立 Home Assistant 容器。' }
    }
}
