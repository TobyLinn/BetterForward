# 环境变量设置指南

本指南将帮助您设置 BetterForward 项目的环境变量。

## 方法一：使用 .env 文件（推荐）

### 1. 创建 .env 文件

在项目根目录创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env

# 或手动创建
touch .env
```

### 2. 编辑 .env 文件

使用文本编辑器打开 `.env` 文件，填入您的配置：

```bash
# 使用 nano 编辑器
nano .env

# 或使用 vim
vim .env

# 或使用 VS Code
code .env
```

### 3. 填入配置值

```env
TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
GROUP_ID=-1001234567890
LANGUAGE=zh_CN
TG_API=
WORKER=2
```

**重要提示**：

- `.env` 文件已添加到 `.gitignore`，不会被提交到 Git
- 不要将 `.env` 文件分享给他人，包含敏感信息

### 4. 运行项目

```bash
./run_with_env.sh
```

## 方法二：使用 export 命令（临时设置）

在终端中直接设置环境变量：

```bash
# 设置环境变量
export TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export GROUP_ID="-1001234567890"
export LANGUAGE="zh_CN"
export WORKER="2"

# 运行项目
./run_with_env.sh
```

**注意**：这种方式设置的环境变量只在当前终端会话有效，关闭终端后会失效。

## 方法三：在命令行中直接设置

```bash
TOKEN="your_token" GROUP_ID="your_group_id" LANGUAGE="zh_CN" ./run_with_env.sh
```

## 方法四：在 shell 配置文件中设置（永久设置）

### macOS/Linux (bash)

编辑 `~/.bashrc` 或 `~/.zshrc`：

```bash
# 编辑配置文件
nano ~/.zshrc  # macOS 默认使用 zsh
# 或
nano ~/.bashrc  # Linux

# 添加以下内容
export TOKEN="your_bot_token_here"
export GROUP_ID="your_group_id_here"
export LANGUAGE="zh_CN"
export WORKER="2"

# 重新加载配置
source ~/.zshrc
# 或
source ~/.bashrc
```

### macOS/Linux (fish shell)

编辑 `~/.config/fish/config.fish`：

```fish
set -x TOKEN "your_bot_token_here"
set -x GROUP_ID "your_group_id_here"
set -x LANGUAGE "zh_CN"
set -x WORKER "2"
```

## 环境变量说明

| 变量名     | 必需 | 说明                                 | 示例值                           |
| ---------- | ---- | ------------------------------------ | -------------------------------- |
| `TOKEN`    | 是   | Telegram Bot Token                   | `1234567890:ABC...`              |
| `GROUP_ID` | 是   | Telegram 群组 ID                     | `-1001234567890`                 |
| `LANGUAGE` | 否   | 界面语言 (`zh_CN`, `en_US`, `ja_JP`) | `zh_CN`                          |
| `TG_API`   | 否   | 自定义 Telegram API 端点             | 留空或 `https://api.example.com` |
| `WORKER`   | 否   | 工作线程数                           | `2`                              |

## 快速设置脚本

您也可以使用以下命令快速创建 `.env` 文件：

```bash
cat > .env << 'EOF'
TOKEN=your_bot_token_here
GROUP_ID=your_group_id_here
LANGUAGE=zh_CN
TG_API=
WORKER=2
EOF
```

然后编辑 `.env` 文件，将 `your_bot_token_here` 和 `your_group_id_here` 替换为实际值。

## 验证环境变量

检查环境变量是否设置正确：

```bash
# 检查单个变量
echo $TOKEN
echo $GROUP_ID

# 检查所有相关变量
env | grep -E "TOKEN|GROUP_ID|LANGUAGE|WORKER|TG_API"
```

## 获取 Bot Token 和 Group ID

### Bot Token

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 命令
3. 按提示设置机器人名称和用户名
4. 获取 Token（格式：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

### Group ID

1. 创建一个 Telegram 群组
2. 将您的机器人添加为管理员
3. 邀请 `@sc_ui_bot` 到群组
4. 在群组中发送 `/id`
5. 获取群组 ID（通常是负数，如：`-1001234567890`）

## 安全建议

1. **不要提交 .env 文件**：`.env` 文件已添加到 `.gitignore`
2. **不要分享 Token**：Token 相当于机器人的密码
3. **定期更换 Token**：如果怀疑泄露，可以通过 @BotFather 重新生成
4. **使用环境变量**：生产环境建议使用环境变量而非硬编码

## 常见问题

### Q: .env 文件不生效？

A: 确保：

- `.env` 文件在项目根目录
- 文件格式正确（没有多余的空格）
- 使用 `./run_with_env.sh` 运行（会自动读取 .env）

### Q: 如何在不同环境使用不同配置？

A: 可以创建多个配置文件：

- `.env.development` - 开发环境
- `.env.production` - 生产环境

然后在使用时指定：

```bash
export $(cat .env.development | xargs)
./run_with_env.sh
```

### Q: 环境变量中有特殊字符怎么办？

A: 使用引号包裹：

```bash
export TOKEN="token_with_special:chars"
```

或在 .env 文件中：

```env
TOKEN="token_with_special:chars"
```
