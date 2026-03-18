# rembg 安装脚本 - 自动尝试兼容版本

Write-Host "开始安装 rembg..." -ForegroundColor Green

# 确保 numpy 1.26.4 已安装
Write-Host "`n步骤1: 检查 numpy 版本..." -ForegroundColor Yellow
python -c "import numpy; print('NumPy version:', numpy.__version__)"

# 尝试的版本列表（从旧到新）
$versions = @("2.0.41", "2.0.42", "2.0.43", "2.0.44", "2.0.45", "2.0.46", "2.0.47", "2.0.48", "2.0.49")

Write-Host "`n步骤2: 尝试安装兼容的 rembg 版本..." -ForegroundColor Yellow

foreach ($version in $versions) {
    Write-Host "`n尝试安装 rembg $version..." -ForegroundColor Cyan
    $result = pip install "rembg==$version" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✓ rembg $version 安装成功！" -ForegroundColor Green
        
        # 验证是否可以导入
        Write-Host "`n步骤3: 验证 rembg 是否可以正常工作..." -ForegroundColor Yellow
        $testResult = python -c "from rembg import new_session; session = new_session('isnet-general-use'); print('rembg session created successfully')" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✓ rembg $version 验证成功！" -ForegroundColor Green
            Write-Host "`n安装完成！使用的版本: rembg $version" -ForegroundColor Green
            exit 0
        } else {
            Write-Host "`n✗ rembg $version 验证失败，继续尝试下一个版本..." -ForegroundColor Red
            pip uninstall rembg -y | Out-Null
        }
    } else {
        Write-Host "✗ rembg $version 安装失败，继续尝试下一个版本..." -ForegroundColor Red
    }
}

Write-Host "`n✗ 所有版本都安装失败！" -ForegroundColor Red
Write-Host "`n建议：" -ForegroundColor Yellow
Write-Host "1. 检查网络连接" -ForegroundColor White
Write-Host "2. 查看上面的错误信息" -ForegroundColor White
Write-Host "3. 如果所有版本都要求 numpy 2.x，考虑使用方案三（PIL背景去除）" -ForegroundColor White
exit 1
