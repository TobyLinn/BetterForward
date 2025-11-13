# GitHub Actions 工作流说明

本目录包含自动构建和推送 Docker 镜像的 GitHub Actions 工作流。

## 工作流文件

### 1. `docker-build.yml` - GitHub Container Registry (推荐)

自动构建并推送到 GitHub Container Registry (ghcr.io)。

**触发条件：**

- 推送到 `main` 或 `master` 分支
- 创建版本标签（如 `v1.0.0`）
- 手动触发（在 GitHub Actions 页面）

**无需配置：** 使用 GitHub 自动生成的 `GITHUB_TOKEN`，无需额外设置。

**镜像地址格式：**

- `ghcr.io/your-username/betterforward:latest`
- `ghcr.io/your-username/betterforward:main-abc1234` (带 commit SHA)
- `ghcr.io/your-username/betterforward:v1.0.0` (版本标签)

### 2. `docker-build-dockerhub.yml` - Docker Hub

自动构建并推送到 Docker Hub。

**触发条件：**

- 推送到 `main` 或 `master` 分支
- 创建版本标签（如 `v1.0.0`）
- 手动触发

**需要配置：** 需要在 GitHub Secrets 中设置：

- `DOCKERHUB_USERNAME`: Docker Hub 用户名
- `DOCKERHUB_PASSWORD`: Docker Hub 密码或访问令牌

**镜像地址格式：**

- `your-username/betterforward:latest`
- `your-username/betterforward:main-abc1234`
- `your-username/betterforward:v1.0.0`

## 设置步骤

### 使用 GitHub Container Registry (推荐，无需额外配置)

1. **启用 GitHub Packages**

   - 默认已启用，无需额外配置
   - 镜像会自动推送到 `ghcr.io`

2. **设置镜像可见性（可选）**

   - 默认镜像为私有
   - 如需公开：在仓库设置 → Packages → 选择包 → Package settings → Change visibility

3. **使用镜像**
   ```yaml
   # docker-compose.yml
   services:
     betterforward:
       image: ghcr.io/your-username/betterforward:latest
       # ... 其他配置
   ```

### 使用 Docker Hub

1. **创建 GitHub Secrets**

   - 进入仓库 Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - 添加以下 secrets：
     - `DOCKERHUB_USERNAME`: 您的 Docker Hub 用户名
     - `DOCKERHUB_PASSWORD`: Docker Hub 密码或访问令牌（推荐使用访问令牌）

2. **创建 Docker Hub 访问令牌（推荐）**

   - 登录 Docker Hub
   - 进入 Account Settings → Security → New Access Token
   - 创建令牌并复制（只显示一次）
   - 将令牌设置为 `DOCKERHUB_PASSWORD` secret

3. **使用镜像**
   ```yaml
   # docker-compose.yml
   services:
     betterforward:
       image: your-username/betterforward:latest
       # ... 其他配置
   ```

## 工作流说明

### 自动触发

- **Push 到主分支**：每次推送到 `main` 或 `master` 分支时自动构建
- **创建标签**：创建版本标签（如 `v1.0.0`）时自动构建
- **Pull Request**：PR 时只构建不推送（用于测试）

### 手动触发

1. 进入 GitHub 仓库的 Actions 页面
2. 选择对应的工作流
3. 点击 "Run workflow"
4. 选择分支并运行

### 多平台构建

工作流支持多平台构建：

- `linux/amd64` (Intel/AMD 64 位)
- `linux/arm64` (ARM 64 位，如 Apple Silicon)

### 缓存优化

使用 GitHub Actions 缓存来加速构建：

- 构建缓存存储在 GitHub Actions 中
- 后续构建会复用缓存，加快速度

## 更新 docker-compose.yml

推送镜像后，更新 `docker-compose.yml` 使用新镜像：

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

## 故障排查

### 构建失败

1. **检查 Dockerfile**：确保 Dockerfile 语法正确
2. **查看构建日志**：在 Actions 页面查看详细错误信息
3. **测试本地构建**：`docker build -t test .`

### 推送失败

1. **GitHub Container Registry**：

   - 检查仓库权限
   - 确保 `GITHUB_TOKEN` 有写入权限

2. **Docker Hub**：
   - 验证 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_PASSWORD` 是否正确
   - 检查 Docker Hub 账户状态

### 镜像不可见

- **GitHub Container Registry**：默认私有，需要在 Package settings 中设置为公开
- **Docker Hub**：检查镜像名称是否正确

## 最佳实践

1. **使用版本标签**：创建版本标签（如 `v1.0.0`）来标记稳定版本
2. **定期更新**：保持 Dockerfile 和依赖更新
3. **安全扫描**：启用 GitHub 的依赖扫描功能
4. **测试构建**：在 PR 中测试构建是否成功
5. **文档更新**：更新 README 中的镜像地址

## 相关资源

- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Hub 文档](https://docs.docker.com/docker-hub/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
