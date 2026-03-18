# GitHub 仓库连接脚本 (PowerShell)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "GitHub 仓库连接设置" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已有远程仓库
$remotes = git remote -v
if ($remotes -match "origin") {
    Write-Host "当前远程仓库：" -ForegroundColor Yellow
    git remote -v
    Write-Host ""
    $update = Read-Host "是否要更新远程仓库 URL？(y/n)"
    if ($update -eq "y" -or $update -eq "Y") {
        $repo_url = Read-Host "请输入新的 GitHub 仓库 URL"
        git remote set-url origin $repo_url
        Write-Host "✅ 远程仓库 URL 已更新" -ForegroundColor Green
    }
} else {
    $repo_url = Read-Host "请输入 GitHub 仓库 URL (例如: https://github.com/username/repo.git 或 git@github.com:username/repo.git)"
    
    if ($repo_url) {
        git remote add origin $repo_url
        Write-Host "✅ 远程仓库已添加" -ForegroundColor Green
        
        $push = Read-Host "是否现在推送到 GitHub？(y/n)"
        if ($push -eq "y" -or $push -eq "Y") {
            git branch -M main
            git push -u origin main
            Write-Host "✅ 代码已推送到 GitHub" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ 未提供仓库 URL" -ForegroundColor Red
    }
}
