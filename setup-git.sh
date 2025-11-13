#!/bin/bash

# Git 仓库设置脚本
# 用于将代码连接到您 fork 的 GitHub 仓库

set -e

echo "=========================================="
echo "Git 仓库设置脚本"
echo "=========================================="
echo ""

# 检查是否已经是 git 仓库
if [ -d .git ]; then
    echo "ℹ️  检测到现有的 git 仓库"
    echo "当前远程仓库配置:"
    git remote -v
    echo ""
    read -p "是否要更新远程仓库地址? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
else
    echo "📦 初始化 git 仓库..."
    git init
    echo "✅ Git 仓库初始化完成"
    echo ""
fi

# 获取用户输入的仓库地址
echo "请输入您 fork 的 GitHub 仓库地址"
echo "例如: https://github.com/your-username/BetterForward.git"
echo "   或: git@github.com:your-username/BetterForward.git"
echo ""
read -p "仓库地址: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ 错误: 仓库地址不能为空"
    exit 1
fi

# 移除现有的 origin（如果存在）
git remote remove origin 2>/dev/null || true

# 添加新的远程仓库
echo ""
echo "🔗 添加远程仓库..."
git remote add origin "$REPO_URL"

# 验证远程仓库
echo ""
echo "✅ 远程仓库已设置:"
git remote -v

echo ""
echo "📋 下一步操作建议:"
echo ""
echo "1. 添加所有文件到 git:"
echo "   git add ."
echo ""
echo "2. 提交更改:"
echo "   git commit -m 'Initial commit from fork'"
echo ""
echo "3. 推送到您的仓库:"
echo "   git push -u origin main"
echo "   或"
echo "   git push -u origin master"
echo ""
echo "4. 添加上游仓库（可选，用于同步原仓库更新）:"
echo "   git remote add upstream https://github.com/SideCloudGroup/BetterForward.git"
echo ""

