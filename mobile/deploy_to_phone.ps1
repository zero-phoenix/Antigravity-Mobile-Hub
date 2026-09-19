<#
.SYNOPSIS
    Transfiere y despliega Antigravity Mobile al celular conectado vía ADB.
#>

Write-Host "`n=== DESPLIEGUE DE ANTIGRAVITY MOBILE HACIA ANDROID ===" -ForegroundColor Cyan

# 1. Comprobar dispositivo conectado
$devices = (& adb devices -l) -split "`r?`n" | Where-Object { $_ -match "^\S+\s+device" }
if (-not $devices) {
    Write-Host "[ERROR] No hay ningún dispositivo conectado en estado 'device'." -ForegroundColor Red
    Write-Host "Ejecuta .\connect.ps1 primero para enlazar tu celular." -ForegroundColor Yellow
    exit 1
}

$deviceId = ($devices[0] -split "\s+")[0]
Write-Host "[✓] Dispositivo detectado: $deviceId" -ForegroundColor Green

# 2. Ruta local y ruta remota de destino
$sourceDir = Join-Path (Split-Path $PSScriptRoot -Parent) "antigravity-mobile"
$targetDir = "/sdcard/Download/antigravity-mobile"

Write-Host "[*] Transfiriendo código hacia el teléfono ($targetDir)..." -ForegroundColor Cyan
& adb -s $deviceId push "$sourceDir" /sdcard/Download/

Write-Host "[✓] Archivos transferidos a /sdcard/Download/antigravity-mobile" -ForegroundColor Green

# 3. Mover a Termux home si Termux tiene permisos o mediante terminal
Write-Host "`nPasos finales para activar en tu teléfono:" -ForegroundColor Yellow
Write-Host "1. Abre Termux en tu celular y ejecuta:" -ForegroundColor White
Write-Host "   termux-setup-storage" -ForegroundColor Cyan
Write-Host "   cp -r /sdcard/Download/antigravity-mobile ~/antigravity-mobile" -ForegroundColor Cyan
Write-Host "   cd ~/antigravity-mobile" -ForegroundColor Cyan
Write-Host "   bash setup_termux.sh" -ForegroundColor Cyan
Write-Host "`n2. Luego inicia el agente con:" -ForegroundColor White
Write-Host "   antigravity" -ForegroundColor Green
Write-Host "`n[✓] Despliegue preparado exitosamente.`n" -ForegroundColor Green
