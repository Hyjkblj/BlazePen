$ErrorActionPreference = "Stop"

function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args,
        [Parameter(Mandatory = $true)][string]$ErrorContext
    )

    & docker @Args
    if ($LASTEXITCODE -ne 0) {
        throw "$ErrorContext (exit code: $LASTEXITCODE)"
    }
}

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $rootDir = Resolve-Path (Join-Path $scriptDir "..")
    $deployDir = Join-Path $rootDir "deploy"
    $composeFile = Join-Path $deployDir "docker-compose.player.yml"
    $envFile = Join-Path $deployDir "player.env"

    if (-not (Test-Path $composeFile)) {
        throw "Compose file not found: $composeFile"
    }

    $composeArgs = @(
        "--project-name", "noendstory",
        "-f", $composeFile
    )

    if (Test-Path $envFile) {
        $composeArgs = @("--project-name", "noendstory", "--env-file", $envFile, "-f", $composeFile)
    }

    Write-Host "Stopping No End Story local stack..." -ForegroundColor Yellow
    Invoke-Docker -Args (@("compose") + $composeArgs + @("down")) -ErrorContext "docker compose down failed"
    Write-Host "Local stack stopped." -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
