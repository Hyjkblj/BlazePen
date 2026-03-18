# Chroma 向量数据库浏览器启动脚本
# 用于快速启动 Gradio UI 工具

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Chroma 向量数据库浏览器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在虚拟环境中
if (-not $env:VIRTUAL_ENV) {
    Write-Host "[提示] 建议在虚拟环境中运行" -ForegroundColor Yellow
    Write-Host "      激活虚拟环境: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# 检查依赖
Write-Host "检查依赖..." -ForegroundColor Yellow
$gradioCheck = python -c "import gradio; print('OK')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[警告] Gradio 未安装，正在安装..." -ForegroundColor Yellow
    pip install gradio pandas
} else {
    Write-Host "[OK] Gradio 已安装" -ForegroundColor Green
}

Write-Host ""
Write-Host "启动浏览器..." -ForegroundColor Yellow
Write-Host "访问地址: http://127.0.0.1:7860" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

# 运行工具
python tools\chroma_auditor.py
