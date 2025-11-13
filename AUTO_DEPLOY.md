# 自动化 Docker 部署指南

本指南说明如何配置 GitHub Actions 实现代码推送后自动构建并上传 Docker 镜像。

## 🚀 快速开始

### 方案一：GitHub Container Registry（推荐，无需额外配置）

1. **推送代码到 GitHub**

   ```bash
   git add .
   git commit -m "Add GitHub Actions for auto build"
   git push origin main
   ```

2. **查看构建状态**

   - 进入 GitHub 仓库页面
   - 点击 "Actions" 标签
   - 查看构建进度和结果

3. **使用自动构建的镜像**
   ```yaml
   # docker-compose.yml
   services:
     betterforward:
       image: ghcr.io/your-username/betterforward:latest
       # ... 其他配置
   ```

### 方案二：Docker Hub（需要配置 Secrets）

1. **配置 GitHub Secrets**

   - 进入仓库 Settings → Secrets and variables → Actions
   - 添加以下 secrets：
     - `DOCKERHUB_USERNAME`: Docker Hub 用户名
     - `DOCKERHUB_PASSWORD`: Docker Hub 密码或访问令牌

2. **推送代码**

   ```bash
   git push origin main
   ```

3. **使用镜像**
   ```yaml
   # docker-compose.yml
   services:
     betterforward:
       image: your-username/betterforward:latest
       # ... 其他配置
   ```

## 📋 详细配置步骤

### GitHub Container Registry 配置

**优点：**

- ✅ 无需额外配置，使用 GitHub Token
- ✅ 与 GitHub 仓库集成
- ✅ 支持私有和公开镜像

**步骤：**

1. **确保工作流文件存在**

   - `.github/workflows/docker-build.yml` 已创建

2. **推送代码触发构建**

   ```bash
   git add .github/workflows/docker-build.yml
   git commit -m "Add auto build workflow"
   git push origin main
   ```

3. **查看构建结果**

   - 在 GitHub 仓库的 Actions 页面查看
   - 构建成功后，镜像会出现在 Packages 页面

4. **设置镜像可见性（可选）**

   - 默认镜像为私有
   - 如需公开：
     - 进入仓库 → Packages
     - 选择包 → Package settings
     - Change visibility → Public

5. **更新 docker-compose.yml**

   ```yaml
   version: "3.8"

   services:
     betterforward:
       image: ghcr.io/your-username/betterforward:latest
       restart: unless-stopped
       environment:
         - TOKEN=${TOKEN}
         - GROUP_ID=${GROUP_ID}
         - LANGUAGE=${LANGUAGE:-zh_CN}
         - TG_API=${TG_API:-}
         - WORKER=${WORKER:-2}
       volumes:
         - ./data:/app/data
   ```

### Docker Hub 配置

**优点：**

- ✅ 使用熟悉的 Docker Hub
- ✅ 支持 Docker Hub 的所有功能

**步骤：**

1. **创建 Docker Hub 访问令牌（推荐）**

   - 登录 [Docker Hub](https://hub.docker.com/)
   - 进入 Account Settings → Security
   - 点击 "New Access Token"
   - 创建令牌并复制（只显示一次）

2. **配置 GitHub Secrets**

   - 进入 GitHub 仓库 → Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - 添加：
     - Name: `DOCKERHUB_USERNAME`
     - Value: 您的 Docker Hub 用户名
   - 再次添加：
     - Name: `DOCKERHUB_PASSWORD`
     - Value: Docker Hub 访问令牌（或密码）

3. **确保工作流文件存在**

   - `.github/workflows/docker-build-dockerhub.yml` 已创建

4. **推送代码**

   ```bash
   git add .github/workflows/docker-build-dockerhub.yml
   git commit -m "Add Docker Hub auto build workflow"
   git push origin main
   ```

5. **更新 docker-compose.yml**

   ```yaml
   version: "3.8"

   services:
     betterforward:
       image: your-username/betterforward:latest
       # ... 其他配置
   ```

## 🔄 工作流触发条件

### 自动触发

1. **推送到主分支**

   - 推送到 `main` 或 `master` 分支时自动构建

   ```bash
   git push origin main
   ```

2. **创建版本标签**

   - 创建版本标签时自动构建并标记版本

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

   - 镜像标签：`ghcr.io/your-username/betterforward:v1.0.0`

3. **Pull Request**
   - PR 时只构建不推送（用于测试构建是否成功）

### 手动触发

1. 进入 GitHub 仓库 → Actions
2. 选择对应的工作流（如 "Build and Push Docker Image"）
3. 点击 "Run workflow"
4. 选择分支并运行

## 📦 镜像标签说明

### GitHub Container Registry

- `latest`: 主分支的最新构建
- `main-abc1234`: 带 commit SHA 的标签
- `v1.0.0`: 版本标签
- `1.0`: 主版本号标签

### Docker Hub

- `latest`: 主分支的最新构建
- `main-abc1234`: 带 commit SHA 的标签
- `v1.0.0`: 版本标签

## 🛠️ 使用自动构建的镜像

### 方法一：使用 docker-compose.yml

```yaml
version: "3.8"

services:
  betterforward:
    # GitHub Container Registry
    image: ghcr.io/your-username/betterforward:latest

    # 或 Docker Hub
    # image: your-username/betterforward:latest

    restart: unless-stopped
    environment:
      - TOKEN=${TOKEN}
      - GROUP_ID=${GROUP_ID}
      - LANGUAGE=${LANGUAGE:-zh_CN}
      - TG_API=${TG_API:-}
      - WORKER=${WORKER:-2}
    volumes:
      - ./data:/app/data
```

然后运行：

```bash
docker compose pull
docker compose up -d
```

### 方法二：直接使用 docker run

```bash
# GitHub Container Registry
docker pull ghcr.io/your-username/betterforward:latest
docker run -d \
  --name betterforward \
  --restart unless-stopped \
  -e TOKEN="your_token" \
  -e GROUP_ID="your_group_id" \
  -e LANGUAGE="zh_CN" \
  -v $(pwd)/data:/app/data \
  ghcr.io/your-username/betterforward:latest

# Docker Hub
docker pull your-username/betterforward:latest
docker run -d \
  --name betterforward \
  --restart unless-stopped \
  -e TOKEN="your_token" \
  -e GROUP_ID="your_group_id" \
  -e LANGUAGE="zh_CN" \
  -v $(pwd)/data:/app/data \
  your-username/betterforward:latest
```

## 🔐 私有镜像访问（GitHub Container Registry）

如果镜像设置为私有，需要登录：

```bash
# 使用 GitHub Personal Access Token
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 或使用密码方式
docker login ghcr.io -u USERNAME -p GITHUB_TOKEN
```

然后拉取镜像：

```bash
docker pull ghcr.io/your-username/betterforward:latest
```

## 📊 监控构建状态

### GitHub Actions 页面

1. 进入仓库 → Actions
2. 查看工作流运行历史
3. 点击具体运行查看详细日志

### 构建通知（可选）

可以配置 GitHub Actions 发送通知：

- 邮件通知（默认）
- Slack/Discord 集成
- 自定义 webhook

## 🔧 故障排查

### 构建失败

1. **检查 Dockerfile**

   ```bash
   # 本地测试构建
   docker build -t test .
   ```

2. **查看构建日志**

   - 在 Actions 页面查看详细错误信息
   - 检查是否有依赖问题

3. **检查权限**
   - GitHub Container Registry: 确保仓库有写入权限
   - Docker Hub: 验证 secrets 配置正确

### 推送失败

1. **GitHub Container Registry**

   - 检查 `GITHUB_TOKEN` 权限
   - 确保仓库设置允许 Actions 写入

2. **Docker Hub**
   - 验证 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_PASSWORD` 正确
   - 检查访问令牌是否有效

### 镜像拉取失败

1. **私有镜像**

   - 确保已登录：`docker login ghcr.io`
   - 检查镜像可见性设置

2. **镜像不存在**
   - 确认镜像名称正确
   - 检查构建是否成功完成

## 💡 最佳实践

1. **使用版本标签**

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **定期更新**

   - 保持 Dockerfile 和依赖更新
   - 定期检查安全漏洞

3. **测试构建**

   - 在 PR 中测试构建
   - 确保构建成功后再合并

4. **文档更新**

   - 更新 README 中的镜像地址
   - 记录版本变更

5. **监控构建**
   - 设置构建失败通知
   - 定期检查构建状态

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Hub 文档](https://docs.docker.com/docker-hub/)
- [Docker Buildx 文档](https://docs.docker.com/buildx/)

## 🎯 完整工作流程示例

```bash
# 1. 修改代码
vim src/utils/captcha.py

# 2. 提交更改
git add .
git commit -m "Fix captcha display issue"

# 3. 推送到 GitHub（自动触发构建）
git push origin main

# 4. 等待构建完成（在 Actions 页面查看）

# 5. 拉取新镜像
docker compose pull

# 6. 重启容器使用新镜像
docker compose up -d
```

## ⚠️ 注意事项

1. **首次构建可能需要较长时间**（下载依赖、构建缓存等）
2. **GitHub Container Registry 有存储限制**（免费账户有限制）
3. **Docker Hub 有拉取限制**（免费账户有速率限制）
4. **确保敏感信息不提交到代码库**（使用环境变量或 secrets）
