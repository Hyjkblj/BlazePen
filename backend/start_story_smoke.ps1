$CliArgs = @($args)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Story Backend Smoke" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script runs story backend smoke tests via run_story_cli.py." -ForegroundColor Yellow
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir

try {
    python .\run_story_cli.py smoke -- @CliArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
