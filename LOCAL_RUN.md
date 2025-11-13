# 本地运行指南

本指南将帮助您在本地运行 BetterForward 项目，用于开发和测试。

## 前置要求

- Python 3.10+ （推荐 3.12）
- pip（Python 包管理器）
- Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）
- Telegram 群组 ID（使用 [@sc_ui_bot](https://t.me/sc_ui_bot) 获取）

## 快速开始

### 1. 检查 Python 版本

```bash
python3 --version
# 或
python --version
```

确保版本 >= 3.10

### 2. 安装依赖

```bash
# 使用 pip 安装依赖
pip3 install -r requirements.txt

# 或使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. 创建数据目录

```bash
mkdir -p ./data
```

### 4. 运行项目

#### 方法一：使用命令行参数

```bash
python3 main.py -token "YOUR_BOT_TOKEN" -group_id "YOUR_GROUP_ID" -language zh_CN
```

#### 方法二：使用环境变量

```bash
export TOKEN="YOUR_BOT_TOKEN"
export GROUP_ID="YOUR_GROUP_ID"
export LANGUAGE="zh_CN"
python3 main.py -token "$TOKEN" -group_id "$GROUP_ID" -language "$LANGUAGE"
```

#### 方法三：使用启动脚本（推荐）

```bash
chmod +x run_local.sh
./run_local.sh
```

## 完整参数说明

```bash
python3 main.py \
  -token "YOUR_BOT_TOKEN" \           # 必需：Telegram Bot Token
  -group_id "YOUR_GROUP_ID" \          # 必需：Telegram 群组 ID
  -language "zh_CN" \                  # 可选：语言 (en_US, zh_CN, ja_JP)，默认 en_US
  -tg_api "" \                         # 可选：自定义 Telegram API 端点
  -workers 2                            # 可选：工作线程数，默认 5
```

## 使用虚拟环境（推荐）

### 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# Windows:
# venv\Scripts\activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行项目

```bash
python main.py -token "YOUR_BOT_TOKEN" -group_id "YOUR_GROUP_ID" -language zh_CN
```

### 退出虚拟环境

```bash
deactivate
```

## 验证安装

运行以下命令验证依赖是否正确安装：

```bash
python3 -c "import telebot; import diskcache; import pytz; import httpx; print('✅ 所有依赖已正确安装')"
```

## 常见问题

### 1. 模块未找到错误

```bash
# 确保已安装所有依赖
pip3 install -r requirements.txt --upgrade
```

### 2. 权限错误

```bash
# 确保数据目录有写权限
chmod 755 ./data
```

### 3. 端口被占用

如果使用自定义 API，确保端口未被占用。

### 4. 数据库迁移问题

首次运行时会自动执行数据库迁移。如果遇到问题：

```bash
# 删除旧数据库（注意：会丢失数据）
rm -f ./data/storage.db

# 重新运行
python3 main.py -token "YOUR_BOT_TOKEN" -group_id "YOUR_GROUP_ID"
```

## 开发模式

### 启用调试日志

修改 `src/config.py`：

```python
logger.setLevel("DEBUG")  # 改为 DEBUG
```

### 使用 IDE 运行

在 PyCharm、VSCode 等 IDE 中：

1. 设置运行配置
2. 参数：`-token "YOUR_TOKEN" -group_id "YOUR_GROUP_ID" -language zh_CN`
3. 工作目录：项目根目录
4. Python 解释器：选择虚拟环境中的 Python

### 代码检查

```bash
# 检查语法错误
python3 -m py_compile main.py src/**/*.py

# 使用 pylint（如果安装）
pylint src/
```

## 测试验证码功能

本地运行后，可以测试增强的验证码功能：

1. 在 Telegram 中向机器人发送消息
2. 机器人会要求验证码（如果启用）
3. 测试不同难度的数学题
4. 测试失败次数限制和锁定机制

## 停止运行

按 `Ctrl+C` 停止程序。

## 数据文件位置

- 数据库：`./data/storage.db`
- 缓存：`./cache/`（diskcache 自动创建）
- 日志：输出到控制台

## 下一步

- 查看 [DEPLOY.md](DEPLOY.md) 了解 Docker 部署
- 查看 [GIT_SETUP.md](GIT_SETUP.md) 了解 Git 配置
- 在 Telegram 群组中发送 `/help` 查看管理菜单
