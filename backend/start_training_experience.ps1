param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Training Backend Full Experience" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will run the full backend training flow:" -ForegroundColor Yellow
Write-Host "1. init-db (unless --skip-init-db is passed)" -ForegroundColor Yellow
Write-Host "2. check-db" -ForegroundColor Yellow
Write-Host "3. full training smoke flow" -ForegroundColor Yellow
Write-Host "4. final report + diagnostics + JSON artifacts" -ForegroundColor Yellow
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir

try {
    python .\run_training_cli.py experience @CliArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
