#!/bin/bash
# GitHub 仓库连接脚本

echo "================================"
echo "GitHub 仓库连接设置"
echo "================================"
echo ""

# 检查是否已有远程仓库
if git remote | grep -q origin; then
    echo "当前远程仓库："
    git remote -v
    echo ""
    read -p "是否要更新远程仓库 URL？(y/n): " update
    if [ "$update" = "y" ] || [ "$update" = "Y" ]; then
        read -p "请输入新的 GitHub 仓库 URL: " repo_url
        git remote set-url origin "$repo_url"
        echo "✅ 远程仓库 URL 已更新"
    fi
else
    read -p "请输入 GitHub 仓库 URL (例如: https://github.com/username/repo.git 或 git@github.com:username/repo.git): " repo_url
    
    if [ -n "$repo_url" ]; then
        git remote add origin "$repo_url"
        echo "✅ 远程仓库已添加"
        
        read -p "是否现在推送到 GitHub？(y/n): " push
        if [ "$push" = "y" ] || [ "$push" = "Y" ]; then
            git branch -M main
            git push -u origin main
            echo "✅ 代码已推送到 GitHub"
        fi
    else
        echo "❌ 未提供仓库 URL"
    fi
fi
