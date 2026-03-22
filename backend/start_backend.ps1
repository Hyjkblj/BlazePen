# 后端启动脚本 - 自动检查并修复 numpy 版本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend Service Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 检查 numpy 版本
Write-Host ""
Write-Host "[1/3] Checking NumPy version..." -ForegroundColor Yellow
$numpyVersion = python -c "import numpy; print(numpy.__version__)" 2>&1

if ($numpyVersion -match "2\.") {
    Write-Host "Detected NumPy 2.x, fixing..." -ForegroundColor Yellow
    pip uninstall numpy -y 2>&1 | Out-Null
    pip install "numpy==1.26.4" --force-reinstall --no-deps 2>&1 | Out-Null
    Write-Host "NumPy fixed to 1.26.4" -ForegroundColor Green
} else {
    Write-Host "NumPy version correct: $numpyVersion" -ForegroundColor Green
}

# 验证依赖
Write-Host ""
Write-Host "[2/3] Verifying core dependencies..." -ForegroundColor Yellow
$testResult = python -c "import numpy; import chromadb; import rembg; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "All dependencies verified" -ForegroundColor Green
} else {
    Write-Host "Dependency verification failed, please check errors" -ForegroundColor Red
    exit 1
}

# 启动后端
Write-Host ""
Write-Host "[3/3] Starting backend service..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the service" -ForegroundColor Cyan
Write-Host ""
python .\run_story_api.py
