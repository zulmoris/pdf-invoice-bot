# update_version.ps1 — обновляет номер версии во всех исходниках
# Использование: powershell -File update_version.ps1 3.2
param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

Write-Host "Обновляю версию на $Version ..."

# 1. bot_v30.py — APP_VERSION = "X.Y"
$botFile = "bot_v30.py"
if (Test-Path $botFile) {
    $content = Get-Content $botFile -Raw
    $content = $content -replace 'APP_VERSION = "[^"]*"', "APP_VERSION = `"$Version`""
    Set-Content $botFile -Value $content -NoNewline
    Write-Host "  OK: $botFile"
}

# 2. dashboard_v30.py — DASH_VERSION = "X.Y"
$dashFile = "dashboard_v30.py"
if (Test-Path $dashFile) {
    $content = Get-Content $dashFile -Raw
    $content = $content -replace 'DASH_VERSION = "[^"]*"', "DASH_VERSION = `"$Version`""
    Set-Content $dashFile -Value $content -NoNewline
    Write-Host "  OK: $dashFile"
}

Write-Host "Версия обновлена: $Version"
