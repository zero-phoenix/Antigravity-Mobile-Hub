<#
.SYNOPSIS
    Audita todos los repositorios de zero-phoenix en GitHub, mostrando visibilidad,
    última actualización y el último release publicado.
#>

Write-Host "`n=== AUDITORÍA DE REPOSITORIOS GITHUB (zero-phoenix) ===" -ForegroundColor Cyan

# 1. Comprobar gh CLI
$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    Write-Host "[ERROR] gh CLI no está instalado o no se encuentra en el PATH." -ForegroundColor Red
    exit 1
}

# 2. Listar repositorios en formato JSON
Write-Host "[*] Obteniendo lista de repositorios..." -ForegroundColor Yellow
$reposJson = & gh repo list zero-phoenix --limit 30 --json name,isPrivate,isArchived,description,updatedAt | ConvertFrom-Json

$results = @()

foreach ($repo in $reposJson) {
    $repoName = $repo.name
    $fullName = "zero-phoenix/$repoName"
    
    # Obtener último release
    $latestRelease = & gh release list --repo $fullName --limit 1 2>$null
    $relText = "(Sin releases)"
    if ($latestRelease) {
        $firstRel = ($latestRelease -split "`r?`n")[0]
        $parts = $firstRel -split "`t"
        if ($parts.Count -ge 3) {
            $relText = "$($parts[2]) ($($parts[0]))"
        } else {
            $relText = $firstRel
        }
    }

    $visibility = if ($repo.isPrivate) { "Privado" } else { "Público" }
    if ($repo.isArchived) { $visibility += " [Archivado]" }

    $results += [PSCustomObject]@{
        Repositorio    = $repoName
        Visibilidad    = $visibility
        UltimoRelease  = $relText
        Actualizado    = ([DateTime]$repo.updatedAt).ToString("yyyy-MM-dd HH:mm")
    }
}

$results | Format-Table -AutoSize

Write-Host ""
Write-Host "[✓] Auditoria completada. Total repositorios analizados: $($results.Count)" -ForegroundColor Green
Write-Host ""
