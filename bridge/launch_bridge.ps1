<#
.SYNOPSIS
    Lanza el servidor Antigravity Bridge en la PC y muestra los enlaces de acceso móvil.
#>

param (
    [int]$Port = 8765,
    [string]$Token = "antigravity-secret-key"
)

Write-Host "`n=== INICIANDO ANTIGRAVITY BRIDGE (PC HOST) ===" -ForegroundColor Cyan

# 1. Obtener dirección IP local de la PC en la red Wi-Fi o Ethernet
$localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.InterfaceAlias -notmatch "Loopback|vEthernet|WSL" -and $_.IPAddress -notmatch "^169\.254" 
} | Select-Object -First 1).IPAddress

if (-not $localIp) {
    $localIp = "127.0.0.1"
}

$mobileUrl = "http://$localIp`:$Port/?token=$Token"
$localUrl  = "http://127.0.0.1:$Port/?token=$Token"

Write-Host "`n[✓] Servidor configurado:" -ForegroundColor Green
Write-Host "    - Enlace Móvil (Wi-Fi) : $mobileUrl" -ForegroundColor Yellow
Write-Host "    - Enlace Local (PC)    : $localUrl" -ForegroundColor Gray
Write-Host "    - Token de Acceso      : $Token" -ForegroundColor Gray

Write-Host "`nPasos para usar en tu celular:" -ForegroundColor White
Write-Host "1. Asegúrate de que tu celular esté conectado a la misma red Wi-Fi que esta PC." -ForegroundColor Gray
Write-Host "2. Abre Google Chrome en tu celular e ingresa a:" -ForegroundColor Gray
Write-Host "   $mobileUrl" -ForegroundColor Cyan
Write-Host "3. (Opcional) En el menú de Chrome, presiona 'Agregar a la pantalla principal' para instalar como App (PWA).`n" -ForegroundColor Gray

# Definir variable de entorno de token para el proceso
$env:ANTIGRAVITY_TOKEN = $Token
$env:PORT = "$Port"

# Ejecutar uvicorn
Set-Location $PSScriptRoot
Write-Host "[*] Iniciando Gateway en puerto $Port..." -ForegroundColor Cyan
python gateway.py
