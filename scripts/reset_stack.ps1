param(
    [switch]$Force
)

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

    if (-not $Force) {
        $answer = Read-Host "This will remove database and vector volumes. Continue? (y/N)"
        if ($answer -ne "y" -and $answer -ne "Y") {
            Write-Host "Cancelled." -ForegroundColor Yellow
            exit 0
        }
    }

    $composeArgs = @(
        "--project-name", "noendstory",
        "-f", $composeFile
    )

    if (Test-Path $envFile) {
        $composeArgs = @("--project-name", "noendstory", "--env-file", $envFile, "-f", $composeFile)
    }

    Write-Host "Resetting No End Story local stack data..." -ForegroundColor Yellow
    Invoke-Docker -Args (@("compose") + $composeArgs + @("down", "--volumes", "--remove-orphans")) -ErrorContext "docker compose reset failed"
    Write-Host "Reset done. Run scripts/start_stack.ps1 to initialize again." -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
