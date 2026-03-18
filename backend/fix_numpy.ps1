# 修复 numpy 版本脚本
# 如果 numpy 被升级到 2.x，运行此脚本降级到 1.26.4

Write-Host "检查当前 NumPy 版本..." -ForegroundColor Yellow
$currentVersion = python -c "import numpy; print(numpy.__version__)" 2>&1
Write-Host "当前版本: $currentVersion" -ForegroundColor Cyan

if ($currentVersion -match "2\.") {
    Write-Host ""
    Write-Host "检测到 NumPy 2.x，正在降级到 1.26.4..." -ForegroundColor Yellow
    pip uninstall numpy -y
    pip install "numpy==1.26.4" --force-reinstall --no-deps
    
    Write-Host ""
    Write-Host "验证安装..." -ForegroundColor Yellow
    $newVersion = python -c "import numpy; print(numpy.__version__)" 2>&1
    Write-Host "新版本: $newVersion" -ForegroundColor Cyan
    
    if ($newVersion -match "1\.26\.4") {
        Write-Host ""
        Write-Host "[OK] NumPy 已成功降级到 1.26.4" -ForegroundColor Green
        
        # 测试 ChromaDB
        Write-Host ""
        Write-Host "测试 ChromaDB..." -ForegroundColor Yellow
        $chromaTest = python -c "import chromadb; print('ChromaDB OK')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] ChromaDB 可以正常导入" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] ChromaDB 导入失败" -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "[ERROR] NumPy 降级失败" -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "[OK] NumPy 版本正确 (1.26.4)" -ForegroundColor Green
}

Write-Host ""
Write-Host "完成！" -ForegroundColor Green
