# Git 仓库设置指南

如果您 fork 了 BetterForward 仓库，本指南将帮助您正确设置 git 远程仓库。

## 情况一：从 GitHub 直接下载的代码（未使用 git clone）

如果您是通过下载 ZIP 文件或直接下载的方式获取的代码，需要先初始化 git 仓库。

### 方法一：使用设置脚本（推荐）

```bash
# 1. 给脚本添加执行权限
chmod +x setup-git.sh

# 2. 运行设置脚本
./setup-git.sh

# 3. 按照提示输入您 fork 的仓库地址
# 例如: https://github.com/your-username/BetterForward.git
```

### 方法二：手动设置

```bash
# 1. 初始化 git 仓库
git init

# 2. 添加您 fork 的仓库作为 origin
git remote add origin https://github.com/your-username/BetterForward.git

# 3. 添加上游仓库（可选，用于同步原仓库更新）
git remote add upstream https://github.com/SideCloudGroup/BetterForward.git

# 4. 添加所有文件
git add .

# 5. 提交更改
git commit -m "Initial commit from fork"

# 6. 推送到您的仓库
git push -u origin main
# 或
git push -u origin master
```

## 情况二：已克隆原仓库，需要切换到您的 fork

如果您已经克隆了原仓库，可以更改远程仓库地址：

```bash
# 1. 查看当前远程仓库
git remote -v

# 2. 更改 origin 指向您的 fork 仓库
git remote set-url origin https://github.com/your-username/BetterForward.git

# 3. （可选）添加上游仓库
git remote add upstream https://github.com/SideCloudGroup/BetterForward.git

# 4. 验证设置
git remote -v
```

## 情况三：重新克隆您的 fork 仓库（最简单）

如果您还没有对代码做太多修改，最简单的方法是重新克隆：

```bash
# 1. 备份您的修改（如果有）
cd ..
cp -r BetterForward BetterForward-backup

# 2. 删除旧目录
rm -rf BetterForward

# 3. 克隆您的 fork 仓库
git clone https://github.com/your-username/BetterForward.git
cd BetterForward

# 4. 添加上游仓库
git remote add upstream https://github.com/SideCloudGroup/BetterForward.git

# 5. 恢复您的修改（如果有）
# 将备份目录中的修改复制回来
```

## 验证设置

设置完成后，验证远程仓库配置：

```bash
git remote -v
```

应该看到类似这样的输出：

```
origin    https://github.com/your-username/BetterForward.git (fetch)
origin    https://github.com/your-username/BetterForward.git (push)
upstream  https://github.com/SideCloudGroup/BetterForward.git (fetch)
upstream  https://github.com/SideCloudGroup/BetterForward.git (push)
```

## 常用 Git 操作

### 提交并推送您的更改

```bash
# 1. 查看更改状态
git status

# 2. 添加更改的文件
git add .

# 3. 提交更改
git commit -m "描述您的更改"

# 4. 推送到您的 fork 仓库
git push origin main
# 或
git push origin master
```

### 同步上游仓库的更新

```bash
# 1. 获取上游仓库的更新
git fetch upstream

# 2. 切换到主分支
git checkout main  # 或 master

# 3. 合并上游更新
git merge upstream/main  # 或 upstream/master

# 4. 解决冲突（如果有）
# 编辑冲突文件，然后：
git add .
git commit -m "Merge upstream updates"

# 5. 推送到您的 fork
git push origin main  # 或 master
```

### 创建新分支进行开发

```bash
# 1. 创建并切换到新分支
git checkout -b feature/your-feature-name

# 2. 进行开发...

# 3. 提交更改
git add .
git commit -m "Add new feature"

# 4. 推送到您的 fork
git push origin feature/your-feature-name

# 5. 在 GitHub 上创建 Pull Request
```

## 注意事项

1. **不要提交敏感信息**：
   - `.env` 文件已添加到 `.gitignore`
   - `data/` 目录已添加到 `.gitignore`
   - 不要提交包含 Bot Token 的配置文件

2. **定期同步上游更新**：
   - 使用 `git fetch upstream` 获取原仓库的更新
   - 定期合并上游更新以保持代码最新

3. **分支命名规范**：
   - `main` 或 `master`: 主分支
   - `feature/xxx`: 新功能分支
   - `fix/xxx`: 修复分支
   - `docs/xxx`: 文档更新分支

4. **提交信息规范**：
   - 使用清晰、描述性的提交信息
   - 使用中文或英文都可以
   - 例如: "增强验证码安全性" 或 "Add enhanced captcha security"

## 获取帮助

如果遇到问题：
- 查看 Git 文档: https://git-scm.com/doc
- GitHub 帮助: https://docs.github.com
- 项目 Issues: https://github.com/SideCloudGroup/BetterForward/issues

