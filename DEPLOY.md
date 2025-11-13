# Docker 部署指南

本指南将帮助您从 GitHub 拉取代码并部署到自己的 Docker 环境中。

## 前置要求

- Docker (版本 20.10+)
- Docker Compose (版本 2.0+)
- Git
- Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）
- Telegram 群组 ID（使用 [@sc_ui_bot](https://t.me/sc_ui_bot) 获取）

## 快速开始

### 方法一：使用 Docker Compose（推荐）

#### 1. 克隆代码

**如果您 fork 了仓库**（推荐）：

```bash
# 克隆您自己的 fork 仓库
git clone https://github.com/your-username/BetterForward.git
cd BetterForward

# 添加上游仓库（用于同步原仓库的更新）
git remote add upstream https://github.com/SideCloudGroup/BetterForward.git
```

**或者从原仓库克隆**：

```bash
git clone https://github.com/SideCloudGroup/BetterForward.git
cd BetterForward
```

**如果您已经下载了代码（不是通过 git clone）**：

```bash
# 进入项目目录
cd BetterForward

# 运行设置脚本
chmod +x setup-git.sh
./setup-git.sh

# 或者手动设置
git init
git remote add origin https://github.com/your-username/BetterForward.git
```

#### 2. 创建环境变量文件（可选）

创建 `.env` 文件来管理环境变量：

```bash
cat > .env << EOF
TOKEN=your_bot_token_here
GROUP_ID=your_group_id_here
LANGUAGE=zh_CN
TG_API=
WORKER=2
EOF
```

然后编辑 `.env` 文件，填入您的实际值：

- `TOKEN`: 您的 Telegram Bot Token
- `GROUP_ID`: 您的 Telegram 群组 ID
- `LANGUAGE`: 语言设置 (`zh_CN`, `en_US`, `ja_JP`)
- `TG_API`: 自定义 API 端点（留空使用默认）
- `WORKER`: 工作线程数（默认 2）

#### 3. 构建并启动容器

使用本地构建的 docker-compose 文件：

```bash
docker compose -f docker-compose.local.yml up -d --build
```

或者直接修改 `docker-compose.yml` 文件，将 `image` 改为 `build`：

```yaml
services:
  betterforward:
    build: . # 改为本地构建
    # ... 其他配置
```

然后运行：

```bash
docker compose up -d --build
```

#### 4. 查看日志

```bash
docker compose logs -f betterforward
```

### 方法二：使用 Docker Run

#### 1. 构建镜像

```bash
docker build -t betterforward:latest .
```

#### 2. 创建数据目录

```bash
mkdir -p ./data
```

#### 3. 运行容器

```bash
docker run -d \
  --name betterforward \
  --restart unless-stopped \
  -e TOKEN="your_bot_token_here" \
  -e GROUP_ID="your_group_id_here" \
  -e LANGUAGE="zh_CN" \
  -e TG_API="" \
  -e WORKER="2" \
  -v $(pwd)/data:/app/data \
  betterforward:latest
```

## 配置说明

### 环境变量

| 变量名     | 必需 | 说明                                 | 默认值         |
| ---------- | ---- | ------------------------------------ | -------------- |
| `TOKEN`    | 是   | Telegram Bot Token                   | -              |
| `GROUP_ID` | 是   | Telegram 群组 ID                     | -              |
| `LANGUAGE` | 否   | 界面语言 (`zh_CN`, `en_US`, `ja_JP`) | `en_US`        |
| `TG_API`   | 否   | 自定义 Telegram API 端点             | 空（使用默认） |
| `WORKER`   | 否   | 工作线程数                           | `2`            |

### 数据持久化

数据目录 `./data` 会被挂载到容器内的 `/app/data`，包含：

- `storage.db`: SQLite 数据库文件
- `spam_keywords.json`: 垃圾关键词配置（如果使用）

**重要**：确保数据目录有正确的权限：

```bash
chmod 755 ./data
```

## 常用操作

### 查看容器状态

```bash
docker compose ps
# 或
docker ps | grep betterforward
```

### 查看日志

```bash
# 实时日志
docker compose logs -f betterforward

# 最近100行日志
docker compose logs --tail=100 betterforward
```

### 停止容器

```bash
docker compose stop betterforward
```

### 启动容器

```bash
docker compose start betterforward
```

### 重启容器

```bash
docker compose restart betterforward
```

### 停止并删除容器

```bash
docker compose down
```

### 更新代码并重新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose -f docker-compose.local.yml up -d --build
```

## 故障排查

### 1. 容器无法启动

检查日志：

```bash
docker compose logs betterforward
```

常见问题：

- Token 或 Group ID 配置错误
- 数据目录权限问题
- 端口冲突

### 2. 数据库迁移失败

如果遇到数据库迁移问题，可以手动运行迁移：

```bash
docker compose exec betterforward python -c "
from src.database import Database
db = Database('/app/data/storage.db')
db.upgrade_db()
"
```

### 3. 验证码功能不工作

确保数据库迁移已成功执行。检查数据库文件：

```bash
docker compose exec betterforward ls -la /app/data/
```

### 4. 查看容器内部文件

```bash
docker compose exec betterforward sh
```

## 生产环境建议

1. **使用环境变量文件**：不要将敏感信息硬编码在配置文件中
2. **定期备份数据**：备份 `./data` 目录
3. **监控日志**：设置日志监控和告警
4. **资源限制**：为容器设置资源限制

```yaml
services:
  betterforward:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 512M
        reservations:
          cpus: "0.5"
          memory: 256M
```

5. **健康检查**：添加健康检查（需要应用支持）

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## 更新和维护

### 自动更新（使用 Watchtower）

```bash
docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  betterforward \
  --interval 3600
```

### 手动更新

**如果您使用的是 fork 仓库**：

```bash
# 1. 拉取上游仓库的更新（如果有设置 upstream）
git fetch upstream
git merge upstream/main  # 或 upstream/master

# 2. 拉取您自己仓库的更新
git pull origin main  # 或 origin/master

# 3. 重新构建镜像
docker compose -f docker-compose.local.yml build

# 4. 重启容器
docker compose -f docker-compose.local.yml up -d
```

**或者直接拉取您的 fork 仓库**：

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker compose -f docker-compose.local.yml build

# 3. 重启容器
docker compose -f docker-compose.local.yml up -d
```

### 同步上游仓库的更新

如果您 fork 了仓库并设置了 upstream，可以这样同步：

```bash
# 1. 获取上游仓库的更新
git fetch upstream

# 2. 切换到主分支
git checkout main  # 或 master

# 3. 合并上游更新
git merge upstream/main  # 或 upstream/master

# 4. 推送到您的 fork 仓库
git push origin main  # 或 origin/master

# 5. 重新部署
docker compose -f docker-compose.local.yml up -d --build
```

## 安全建议

1. **保护 Bot Token**：不要将 Token 提交到 Git 仓库
2. **限制访问**：使用防火墙限制容器网络访问
3. **定期更新**：保持 Docker 镜像和依赖包更新
4. **备份数据**：定期备份数据库文件

## 获取帮助

- GitHub Issues: https://github.com/SideCloudGroup/BetterForward/issues
- Telegram 频道: [@betterforward](https://t.me/betterforward)

## 示例：完整部署流程

### 使用 Fork 仓库部署

```bash
# 1. 克隆您 fork 的代码（替换 your-username 为您的 GitHub 用户名）
git clone https://github.com/your-username/BetterForward.git
cd BetterForward

# 2. （可选）添加上游仓库用于同步更新
git remote add upstream https://github.com/SideCloudGroup/BetterForward.git

# 2. 创建环境变量文件
cat > .env << EOF
TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
GROUP_ID=-1001234567890
LANGUAGE=zh_CN
TG_API=
WORKER=2
EOF

# 3. 创建数据目录
mkdir -p ./data

# 4. 构建并启动
docker compose -f docker-compose.local.yml up -d --build

# 5. 查看日志确认运行正常
docker compose logs -f betterforward
```

部署完成后，在 Telegram 群组中发送 `/help` 命令来查看管理菜单。
