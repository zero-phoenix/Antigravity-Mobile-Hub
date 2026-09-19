<#
.SYNOPSIS
    Configura y persiste la GEMINI_API_KEY en el entorno de Windows.
.PARAMETER ApiKey
    La clave de API obtenida de Google AI Studio (https://aistudio.google.com/).
#>

param (
    [Parameter(Mandatory=$false)]
    [string]$ApiKey = ""
)

Write-Host "`n=== CONFIGURACIÓN DE GOOGLE GEMINI API ===" -ForegroundColor Cyan

if (-not $ApiKey) {
    $existing = [System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
    if ($existing) {
        $masked = $existing.Substring(0, [Math]::Min(8, $existing.Length)) + "..." + $existing.Substring([Math]::Max(0, $existing.Length - 4))
        Write-Host "[✓] Clave actual en entorno User: $masked" -ForegroundColor Green
        $confirm = Read-Host "¿Deseas sobrescribirla? (s/N)"
        if ($confirm -ne "s" -and $confirm -ne "S") {
            Write-Host "[*] Manteniendo clave existente." -ForegroundColor Yellow
            $env:GEMINI_API_KEY = $existing
            & python (Join-Path $PSScriptRoot "test_gemini.py")
            exit 0
        }
    }

    Write-Host "`nObtén tu API key gratuita en: https://aistudio.google.com/apikey" -ForegroundColor Yellow
    $ApiKey = Read-Host "Pega tu GEMINI_API_KEY aquí"
}

if (-not $ApiKey) {
    Write-Host "[ERROR] No se ingresó ninguna clave." -ForegroundColor Red
    exit 1
}

# Guardar de forma persistente en las variables de entorno de Usuario
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $ApiKey.Trim(), "User")
$env:GEMINI_API_KEY = $ApiKey.Trim()

Write-Host "[✓] GEMINI_API_KEY guardada exitosamente en el entorno de Usuario de Windows." -ForegroundColor Green

# Ejecutar prueba de verificación
Write-Host "`n[*] Probando conectividad con Gemini API..." -ForegroundColor Cyan
& python (Join-Path $PSScriptRoot "test_gemini.py")
