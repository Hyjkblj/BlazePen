param(
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"

function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args,
        [Parameter(Mandatory = $true)][string]$ErrorContext,
        [switch]$Silent
    )

    if ($Silent) {
        & docker @Args | Out-Null
    } else {
        & docker @Args
    }

    if ($LASTEXITCODE -ne 0) {
        throw "$ErrorContext (exit code: $LASTEXITCODE)"
    }
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Key,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path $FilePath)) {
        return $DefaultValue
    }

    $line = Get-Content -Path $FilePath | Where-Object { $_ -match "^\s*$Key=" } | Select-Object -First 1
    if (-not $line) {
        return $DefaultValue
    }

    return ($line -replace "^\s*$Key=", "").Trim()
}

function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $content = Get-Content -Path $FilePath
    $updated = $false
    $newContent = foreach ($line in $content) {
        if ($line -match "^\s*$Key=") {
            $updated = $true
            "$Key=$Value"
        } else {
            $line
        }
    }

    if (-not $updated) {
        $newContent += "$Key=$Value"
    }

    Set-Content -Path $FilePath -Value $newContent -Encoding UTF8
}

function Ensure-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker command not found. Please install and start Docker Desktop first."
    }

    Invoke-Docker -Args @("compose", "version") -ErrorContext "docker compose is unavailable" -Silent
    Invoke-Docker -Args @("info") -ErrorContext "docker engine is unavailable" -Silent
}

function Wait-BackendHealthy {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutSec = 120
    )

    $healthUrl = "http://127.0.0.1:$Port/health"
    $deadline = (Get-Date).AddSeconds($TimeoutSec)

    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 3
            if ($resp.status -eq "healthy") {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    return $false
}

function Sync-DefaultSceneImages {
    param(
        [Parameter(Mandatory = $true)][string]$RootDir,
        [string]$ContainerName = "noendstory-backend",
        [string]$ContainerSceneDir = "/data/images/scenes"
    )

    $localSceneDir = Join-Path $RootDir "backend/images/scenes"
    if (-not (Test-Path $localSceneDir)) {
        Write-Host "Skip scene image sync: local dir not found ($localSceneDir)" -ForegroundColor DarkYellow
        return
    }

    $imageExts = @(".jpg", ".jpeg", ".png", ".webp")
    $localImages = Get-ChildItem -Path $localSceneDir -File | Where-Object {
        $imageExts -contains $_.Extension.ToLowerInvariant()
    }

    if ($localImages.Count -eq 0) {
        Write-Host "Skip scene image sync: no images found in $localSceneDir" -ForegroundColor DarkYellow
        return
    }

    Invoke-Docker -Args @("exec", $ContainerName, "sh", "-lc", "mkdir -p $ContainerSceneDir") -ErrorContext "prepare scene image directory failed"

    $copied = 0
    $skipped = 0
    foreach ($img in $localImages) {
        $targetPath = "$ContainerSceneDir/$($img.Name)"
        & docker exec $ContainerName sh -lc "test -f '$targetPath'"
        if ($LASTEXITCODE -eq 0) {
            $skipped++
            continue
        }

        Invoke-Docker -Args @("cp", $img.FullName, "${ContainerName}:$targetPath") -ErrorContext "copy scene image failed: $($img.Name)"
        $copied++
    }

    if ($copied -gt 0) {
        Write-Host "Synced default scene images: copied=$copied, existing=$skipped" -ForegroundColor Green
    } else {
        Write-Host "Default scene images already present: $skipped files" -ForegroundColor Green
    }
}

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $rootDir = Resolve-Path (Join-Path $scriptDir "..")
    $deployDir = Join-Path $rootDir "deploy"
    $composeFile = Join-Path $deployDir "docker-compose.player.yml"
    $envTemplate = Join-Path $deployDir "player.env.example"
    $envFile = Join-Path $deployDir "player.env"

    if (-not (Test-Path $composeFile)) {
        throw "Compose file not found: $composeFile"
    }
    if (-not (Test-Path $envTemplate)) {
        throw "Env template not found: $envTemplate"
    }

    Write-Host "== No End Story local stack startup ==" -ForegroundColor Cyan
    Write-Host "1) Check Docker runtime" -ForegroundColor Yellow
    Ensure-DockerReady

    if (-not (Test-Path $envFile)) {
        Write-Host "2) Create player env file: deploy/player.env" -ForegroundColor Yellow
        Copy-Item -Path $envTemplate -Destination $envFile
    }

    $password = Get-EnvValue -FilePath $envFile -Key "POSTGRES_PASSWORD"
    if ([string]::IsNullOrWhiteSpace($password)) {
        $password = [Guid]::NewGuid().ToString("N")
        Set-EnvValue -FilePath $envFile -Key "POSTGRES_PASSWORD" -Value $password
        Write-Host "Generated POSTGRES_PASSWORD and wrote it to deploy/player.env" -ForegroundColor Green
    }

    $backendImage = Get-EnvValue -FilePath $envFile -Key "BACKEND_IMAGE" -DefaultValue "ghcr.io/no-end-story/no-end-story-backend:latest"
    $backendPort = Get-EnvValue -FilePath $envFile -Key "BACKEND_PORT" -DefaultValue "8000"
    $backendPortInt = [int]$backendPort

    $composeArgs = @(
        "--project-name", "noendstory",
        "--env-file", $envFile,
        "-f", $composeFile
    )

    if (-not $SkipPull) {
        Write-Host "3) Pull image: $backendImage" -ForegroundColor Yellow
        Invoke-Docker -Args (@("compose") + $composeArgs + @("pull")) -ErrorContext "docker compose pull failed"
    }

    Write-Host "4) Start PostgreSQL + backend containers" -ForegroundColor Yellow
    Invoke-Docker -Args (@("compose") + $composeArgs + @("up", "-d")) -ErrorContext "docker compose up failed"

    Write-Host "5) Sync default scene images" -ForegroundColor Yellow
    Sync-DefaultSceneImages -RootDir $rootDir

    Write-Host "6) Wait for backend health" -ForegroundColor Yellow
    if (Wait-BackendHealthy -Port $backendPortInt -TimeoutSec 120) {
        Write-Host "Backend is healthy: http://127.0.0.1:$backendPortInt/health" -ForegroundColor Green
        exit 0
    }

    Write-Host "Backend health check timed out. Showing container status and logs..." -ForegroundColor Red
    try {
        & docker compose @composeArgs ps
        & docker compose @composeArgs logs --tail 80 backend postgres
    } catch {
        Write-Host "Failed to fetch docker status/logs: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    exit 1
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Message -like "*docker engine is unavailable*") {
        Write-Host "Hint: start Docker Desktop first, then rerun this script." -ForegroundColor Yellow
    }
    exit 1
}
