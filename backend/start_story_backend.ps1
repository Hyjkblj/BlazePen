# Story backend standalone startup script
# Notes:
# 1. Starts only the story backend service (default port 8000).
# 2. Uses run_story_api.py as the canonical story entrypoint.

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Story Backend Service Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/2] Verifying story-service dependencies..." -ForegroundColor Yellow
$testResult = python -c "import fastapi, uvicorn, sqlalchemy; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Story-service dependencies verified" -ForegroundColor Green
} else {
    Write-Host "Dependency verification failed, please check errors" -ForegroundColor Red
    Write-Host $testResult
    exit 1
}

if (-not $env:STORY_API_PORT) {
    $env:STORY_API_PORT = "8000"
}

Write-Host ""
Write-Host "[2/2] Starting story backend service..." -ForegroundColor Yellow
Write-Host "Docs: http://localhost:$($env:STORY_API_PORT)/docs" -ForegroundColor Cyan
Write-Host "Health: http://localhost:$($env:STORY_API_PORT)/health" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the service" -ForegroundColor Cyan
Write-Host ""
python .\run_story_api.py
