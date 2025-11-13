# Docker Hub 配置指南

本指南将帮助您配置 GitHub Actions 自动构建并推送到 Docker Hub。

## 📋 前置要求

- ✅ 已创建 Docker Hub 账户
- ✅ 已创建 GitHub 仓库
- ✅ 已 fork 或拥有 BetterForward 仓库

## 🚀 快速配置步骤

### 步骤 1: 创建 Docker Hub 访问令牌

**推荐使用访问令牌而不是密码，更安全！**

1. **登录 Docker Hub**

   - 访问 [https://hub.docker.com/](https://hub.docker.com/)
   - 使用您的账户登录

2. **创建访问令牌**

   - 点击右上角头像 → **Account Settings**
   - 左侧菜单选择 **Security**
   - 点击 **New Access Token** 按钮
   - 填写令牌描述（如：`GitHub Actions for BetterForward`）
   - 选择权限：**Read & Write**（读写权限）
   - 点击 **Generate** 生成令牌

3. **复制令牌**
   - ⚠️ **重要**：令牌只显示一次，请立即复制保存
   - 如果丢失，需要重新创建

### 步骤 2: 配置 GitHub Secrets

1. **进入 GitHub 仓库设置**

   - 打开您的 GitHub 仓库页面
   - 点击 **Settings** 标签

2. **打开 Secrets 配置**

   - 左侧菜单选择 **Secrets and variables** → **Actions**
   - 点击 **New repository secret** 按钮

3. **添加 Docker Hub 用户名**

   - Name: `DOCKERHUB_USERNAME`
   - Value: 您的 Docker Hub 用户名（例如：`yourusername`）
   - 点击 **Add secret**

4. **添加 Docker Hub 密码/令牌**
   - 再次点击 **New repository secret**
   - Name: `DOCKERHUB_PASSWORD`
   - Value: 刚才创建的访问令牌（或您的 Docker Hub 密码）
   - 点击 **Add secret**

### 步骤 3: 确认工作流文件存在

确保以下文件存在：

- `.github/workflows/docker-build-dockerhub.yml`

如果不存在，请从仓库中获取。

### 步骤 4: 更新 docker-compose.yml（可选）

更新 `docker-compose.yml` 使用您的 Docker Hub 镜像：

```yaml
version: "3.8"

services:
  betterforward:
    image: your-dockerhub-username/betterforward:latest
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

**替换 `your-dockerhub-username` 为您的实际 Docker Hub 用户名**

### 步骤 5: 推送代码触发构建

```bash
# 添加工作流文件（如果还没有提交）
git add .github/workflows/docker-build-dockerhub.yml

# 提交更改
git commit -m "Configure Docker Hub auto build"

# 推送到 GitHub（会自动触发构建）
git push origin main
```

### 步骤 6: 查看构建结果

1. **查看 Actions**

   - 进入 GitHub 仓库页面
   - 点击 **Actions** 标签
   - 查看 "Build and Push to Docker Hub" 工作流
   - 等待构建完成（通常 5-10 分钟）

2. **验证镜像**
   - 登录 Docker Hub
   - 进入您的账户页面
   - 应该能看到 `betterforward` 仓库
   - 点击查看镜像标签（latest, main-xxx 等）

## 🔍 验证配置

### 检查 Secrets 配置

在 GitHub 仓库中：

- Settings → Secrets and variables → Actions
- 确认看到：
  - ✅ `DOCKERHUB_USERNAME`
  - ✅ `DOCKERHUB_PASSWORD`

### 测试构建

1. **手动触发构建**

   - 进入 Actions 页面
   - 选择 "Build and Push to Docker Hub"
   - 点击 "Run workflow"
   - 选择分支并运行

2. **查看构建日志**
   - 点击运行中的工作流
   - 查看每个步骤的日志
   - 确认没有错误

### 测试拉取镜像

```bash
# 拉取镜像（替换为您的用户名）
docker pull your-dockerhub-username/betterforward:latest

# 查看镜像
docker images | grep betterforward
```

## 📦 镜像标签说明

构建成功后，Docker Hub 上会有以下标签：

- `latest`: 主分支的最新构建
- `main-abc1234`: 带 commit SHA 的标签（如 `main-abc1234`）
- `v1.0.0`: 版本标签（如果创建了版本标签）
- `1.0`: 主版本号标签

## 🛠️ 使用自动构建的镜像

### 方法一：使用 docker-compose.yml

```yaml
version: "3.8"

services:
  betterforward:
    image: your-dockerhub-username/betterforward:latest
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
docker pull your-dockerhub-username/betterforward:latest

docker run -d \
  --name betterforward \
  --restart unless-stopped \
  -e TOKEN="your_bot_token" \
  -e GROUP_ID="your_group_id" \
  -e LANGUAGE="zh_CN" \
  -v $(pwd)/data:/app/data \
  your-dockerhub-username/betterforward:latest
```

## 🔧 故障排查

### 问题 1: 构建失败 - 认证错误

**错误信息：**

```
Error: Cannot perform an interactive login from a non TTY device
```

**解决方法：**

1. 检查 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_PASSWORD` 是否正确
2. 确认访问令牌有读写权限
3. 如果使用密码，确保密码正确

### 问题 2: 构建失败 - 权限不足

**错误信息：**

```
denied: requested access to the resource is denied
```

**解决方法：**

1. 确认访问令牌权限为 **Read & Write**
2. 检查 Docker Hub 账户状态是否正常
3. 确认镜像名称格式正确：`username/betterforward`

### 问题 3: 镜像名称错误

**错误信息：**

```
invalid reference format
```

**解决方法：**

1. 确认 Docker Hub 用户名不包含特殊字符
2. 镜像名称格式：`username/repository-name`
3. 检查工作流文件中的镜像名称配置

### 问题 4: 构建超时

**解决方法：**

1. 多平台构建（amd64 + arm64）需要较长时间
2. 可以临时禁用多平台构建，只构建 amd64：
   ```yaml
   platforms: linux/amd64
   ```

### 问题 5: 找不到 Secrets

**解决方法：**

1. 确认 Secrets 名称完全匹配：
   - `DOCKERHUB_USERNAME`（全大写）
   - `DOCKERHUB_PASSWORD`（全大写）
2. 确认在正确的仓库中配置 Secrets
3. 检查是否有拼写错误

## 💡 最佳实践

1. **使用访问令牌而不是密码**

   - 更安全
   - 可以随时撤销
   - 可以设置过期时间

2. **定期更新令牌**

   - 建议每 90 天更新一次
   - 如果怀疑泄露，立即撤销并重新创建

3. **使用版本标签**

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

   - 创建稳定的版本镜像
   - 方便回滚

4. **监控构建状态**

   - 设置构建失败通知
   - 定期检查 Docker Hub 镜像更新

5. **保护 Secrets**
   - 不要将 Secrets 提交到代码库
   - 不要在日志中输出 Secrets
   - 使用 GitHub Secrets 管理敏感信息

## 📊 工作流触发说明

### 自动触发

- ✅ **推送到 main/master 分支**：每次 push 自动构建
- ✅ **创建版本标签**：创建 `v*` 标签时自动构建
- ❌ **Pull Request**：PR 时不构建（避免泄露 Secrets）

### 手动触发

1. 进入 Actions 页面
2. 选择 "Build and Push to Docker Hub"
3. 点击 "Run workflow"
4. 选择分支并运行

## 🎯 完整示例

假设您的 Docker Hub 用户名是 `myusername`：

1. **配置 Secrets**

   - `DOCKERHUB_USERNAME` = `myusername`
   - `DOCKERHUB_PASSWORD` = `dckr_pat_xxxxxxxxxxxxx`（访问令牌）

2. **更新 docker-compose.yml**

   ```yaml
   image: myusername/betterforward:latest
   ```

3. **推送代码**

   ```bash
   git push origin main
   ```

4. **查看结果**

   - GitHub Actions: 构建成功
   - Docker Hub: `myusername/betterforward:latest` 可用

5. **使用镜像**
   ```bash
   docker pull myusername/betterforward:latest
   docker compose up -d
   ```

## 📚 相关资源

- [Docker Hub 文档](https://docs.docker.com/docker-hub/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker Hub 访问令牌指南](https://docs.docker.com/docker-hub/access-tokens/)

## ⚠️ 注意事项

1. **免费账户限制**

   - Docker Hub 免费账户有拉取速率限制
   - 建议使用 GitHub Container Registry 作为备选

2. **镜像公开性**

   - 默认镜像为公开
   - 如需私有，需要 Docker Hub Pro 账户

3. **构建时间**

   - 首次构建可能需要 10-15 分钟
   - 后续构建因为有缓存会更快（5-10 分钟）

4. **多平台构建**
   - 当前配置支持 amd64 和 arm64
   - 如果只需要 amd64，可以修改 `platforms` 配置

## ✅ 配置检查清单

- [ ] 已创建 Docker Hub 账户
- [ ] 已创建访问令牌（或使用密码）
- [ ] 已在 GitHub 配置 `DOCKERHUB_USERNAME` Secret
- [ ] 已在 GitHub 配置 `DOCKERHUB_PASSWORD` Secret
- [ ] 已确认工作流文件存在
- [ ] 已更新 docker-compose.yml（如需要）
- [ ] 已推送代码触发构建
- [ ] 已验证构建成功
- [ ] 已在 Docker Hub 看到镜像

完成以上步骤后，您的 Docker 镜像就会自动构建并推送到 Docker Hub 了！🎉
