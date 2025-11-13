#!/bin/bash

# BetterForward Docker 部署脚本
# 使用方法: ./deploy.sh

set -e

echo "=========================================="
echo "BetterForward Docker 部署脚本"
echo "=========================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未找到 Docker，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: 未找到 Docker Compose，请先安装 Docker Compose"
    exit 1
fi

# 检查是否存在 .env 文件
if [ ! -f .env ]; then
    echo "📝 创建 .env 文件..."
    cat > .env << 'EOF'
TOKEN=your_bot_token_here
GROUP_ID=your_group_id_here
LANGUAGE=zh_CN
TG_API=
WORKER=2
EOF
    echo "✅ .env 文件已创建"
    echo ""
    echo "⚠️  请编辑 .env 文件，填入您的 Bot Token 和 Group ID"
    echo "   然后再次运行此脚本"
    exit 0
fi

# 读取环境变量
source .env

# 检查必要的环境变量
if [ "$TOKEN" = "your_bot_token_here" ] || [ -z "$TOKEN" ]; then
    echo "❌ 错误: 请在 .env 文件中设置 TOKEN"
    exit 1
fi

if [ "$GROUP_ID" = "your_group_id_here" ] || [ -z "$GROUP_ID" ]; then
    echo "❌ 错误: 请在 .env 文件中设置 GROUP_ID"
    exit 1
fi

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p ./data
chmod 755 ./data

# 检查是否已有运行的容器
if docker ps -a --format '{{.Names}}' | grep -q "^betterforward$"; then
    echo "⚠️  检测到已存在的容器"
    read -p "是否要停止并删除现有容器? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 停止并删除现有容器..."
        docker compose -f docker-compose.local.yml down 2>/dev/null || true
        docker stop betterforward 2>/dev/null || true
        docker rm betterforward 2>/dev/null || true
    else
        echo "ℹ️  保留现有容器，将尝试更新..."
    fi
fi

# 构建并启动容器
echo ""
echo "🔨 构建 Docker 镜像..."
docker compose -f docker-compose.local.yml build

echo ""
echo "🚀 启动容器..."
docker compose -f docker-compose.local.yml up -d

# 等待容器启动
echo ""
echo "⏳ 等待容器启动..."
sleep 3

# 检查容器状态
if docker ps --format '{{.Names}}' | grep -q "^betterforward$"; then
    echo ""
    echo "✅ 部署成功！"
    echo ""
    echo "📊 容器状态:"
    docker ps --filter "name=betterforward" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "📋 查看日志: docker compose -f docker-compose.local.yml logs -f betterforward"
    echo "🛑 停止容器: docker compose -f docker-compose.local.yml stop"
    echo "🔄 重启容器: docker compose -f docker-compose.local.yml restart"
    echo ""
    echo "💡 提示: 在 Telegram 群组中发送 /help 查看管理菜单"
else
    echo ""
    echo "❌ 容器启动失败，请查看日志:"
    echo "   docker compose -f docker-compose.local.yml logs betterforward"
    exit 1
fi

