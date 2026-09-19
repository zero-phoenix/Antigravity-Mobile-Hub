<#
.SYNOPSIS
    Lanza control visual de pantalla completa o ventana del celular con scrcpy.
#>

$scrcpy = Get-Command scrcpy -ErrorAction SilentlyContinue
if (-not $scrcpy) {
    Write-Host "[*] scrcpy no está instalado. Instalando vía winget..." -ForegroundColor Yellow
    winget install Genymobile.scrcpy --silent --accept-package-agreements --accept-source-agreements
}

Write-Host "[*] Iniciando scrcpy (control de pantalla)..." -ForegroundColor Cyan
scrcpy --always-on-top --stay-awake --turn-screen-off
