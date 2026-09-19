<#
.SYNOPSIS
    Conector y Administrador de Conexión Móvil (ADB USB / Wi-Fi) para Antigravity.
.DESCRIPTION
    Detecta dispositivos Android conectados, configura ADB sobre TCP/IP (Wi-Fi),
    obtiene la IP del dispositivo y verifica el entorno para desplegar Antigravity Mobile.
#>

param (
    [string]$DeviceIp = "",
    [int]$Port = 5555,
    [switch]$WirelessOnly
)

Write-Host "`n=== ANTIGRAVITY MOBILE BRIDGE ===" -ForegroundColor Cyan

# 1. Verificar binario de ADB
$adbPath = (Get-Command adb -ErrorAction SilentlyContinue).Source
if (-not $adbPath) {
    Write-Host "[ERROR] ADB no está en el PATH. Verifica la instalación de platform-tools." -ForegroundColor Red
    exit 1
}
Write-Host "[✓] ADB detectado: $adbPath" -ForegroundColor Green

# 2. Si se pasó una IP directamente para conexión inalámbrica
if ($DeviceIp) {
    Write-Host "[*] Intentando conectar de forma inalámbrica a $DeviceIp:$Port..." -ForegroundColor Yellow
    & adb connect "$DeviceIp`:$Port"
    Start-Sleep -Seconds 1
}

# 3. Comprobar dispositivos conectados
$devicesOutput = & adb devices -l
$lines = $devicesOutput -split "`r?`n" | Where-Object { $_ -match "^\S+\s+(device|unauthorized|offline)" }

if (-not $lines -or $lines.Count -eq 0) {
    Write-Host "`n[!] No se detectó ningún dispositivo Android conectado." -ForegroundColor Yellow
    Write-Host "`nPasos para conectar:" -ForegroundColor White
    Write-Host " 1. En tu celular, ve a Ajustes > Opciones de Desarrollador > Activa 'Depuración por USB'." -ForegroundColor Gray
    Write-Host " 2. Conecta el celular a la PC con cable USB." -ForegroundColor Gray
    Write-Host " 3. En la pantalla del celular, acepta la huella digital RSA ('Permitir siempre')." -ForegroundColor Gray
    Write-Host " 4. Vuelve a ejecutar este script." -ForegroundColor Cyan
    Write-Host "`nSi deseas conectar por Wi-Fi directo (Android 11+):" -ForegroundColor White
    Write-Host "   adb pair <IP>:<PUERTO_VINCULACION> <CODIGO>" -ForegroundColor Gray
    Write-Host "   .\connect.ps1 -DeviceIp <IP> -Port <PUERTO_CONEXION>`n" -ForegroundColor Gray
    exit 0
}

Write-Host "`n[✓] Dispositivos detectados:" -ForegroundColor Green
foreach ($line in $lines) {
    Write-Host "    $line" -ForegroundColor White
}

# 4. Obtener información del primer dispositivo conectado
$deviceId = ($lines[0] -split "\s+")[0]
$status = ($lines[0] -split "\s+")[1]

if ($status -eq "unauthorized") {
    Write-Host "`n[!] Dispositivo $deviceId detectado pero NO AUTORIZADO." -ForegroundColor Red
    Write-Host "    Por favor desbloquea la pantalla de tu celular y presiona 'Permitir' en la ventana emergente de depuración USB." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[*] Extrayendo información de $deviceId..." -ForegroundColor Cyan
$model = (& adb -s $deviceId shell getprop ro.product.model).Trim()
$brand = (& adb -s $deviceId shell getprop ro.product.brand).Trim()
$androidVer = (& adb -s $deviceId shell getprop ro.build.version.release).Trim()
$battery = (& adb -s $deviceId shell dumpsys battery | Select-String "level:").ToString().Trim()

Write-Host "    Marca / Modelo : $brand $model" -ForegroundColor White
Write-Host "    Android Versión: $androidVer" -ForegroundColor White
Write-Host "    $battery%" -ForegroundColor White

# 5. Obtener dirección IP Wi-Fi del celular
$wlanIp = (& adb -s $deviceId shell "ip -f inet addr show wlan0 2>/dev/null" | Select-String "inet\s+(\d+\.\d+\.\d+\.\d+)")
if ($wlanIp -match "inet\s+(\d+\.\d+\.\d+\.\d+)") {
    $phoneIp = $matches[1]
    Write-Host "    IP Wi-Fi       : $phoneIp" -ForegroundColor Yellow
    
    # Habilitar TCP/IP para desconectar el cable
    Write-Host "`n[*] Configurando ADB en modo TCP/IP (puerto $Port)..." -ForegroundColor Cyan
    & adb -s $deviceId tcpip $Port
    Start-Sleep -Seconds 2
    Write-Host "[✓] Modo inalámbrico listo. Ya puedes desconectar el cable USB y usar:" -ForegroundColor Green
    Write-Host "    adb connect $phoneIp`:$Port" -ForegroundColor Cyan
} else {
    Write-Host "    [!] Wi-Fi no conectado o interfaz wlan0 no detectada." -ForegroundColor Gray
}

# 6. Comprobar Termux en el celular
Write-Host "`n[*] Verificando paquetes en el dispositivo..." -ForegroundColor Cyan
$termuxInstalled = & adb -s $deviceId shell "pm list packages | grep com.termux"
if ($termuxInstalled -match "com.termux") {
    Write-Host "    [✓] Termux instalado en el celular." -ForegroundColor Green
} else {
    Write-Host "    [!] Termux NO detectado. Descárgalo desde F-Droid para el port de Antigravity:" -ForegroundColor Yellow
    Write-Host "        https://f-droid.org/packages/com.termux/" -ForegroundColor Gray
}

Write-Host "`n=== Conexión lista y verificada ===`n" -ForegroundColor Green
