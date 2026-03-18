# 训练引擎专用启动脚本
# 说明：
# 1. 这个脚本只启动训练服务，不检查 Chroma、Rembg、TTS 等非训练链路依赖。
# 2. 默认监听 8010 端口，避免和完整后端服务冲突。

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Training Engine Service Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/2] Verifying training-service dependencies..." -ForegroundColor Yellow
$testResult = python -c "import fastapi, uvicorn, sqlalchemy; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Training-service dependencies verified" -ForegroundColor Green
} else {
    Write-Host "Dependency verification failed, please check errors" -ForegroundColor Red
    Write-Host $testResult
    exit 1
}

if (-not $env:TRAINING_API_PORT) {
    $env:TRAINING_API_PORT = "8010"
}

Write-Host ""
Write-Host "[2/2] Starting training engine service..." -ForegroundColor Yellow
Write-Host "Docs: http://localhost:$($env:TRAINING_API_PORT)/docs" -ForegroundColor Cyan
Write-Host "Health: http://localhost:$($env:TRAINING_API_PORT)/health" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the service" -ForegroundColor Cyan
Write-Host ""
python .\run_training_api.py
