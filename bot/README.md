# Nyx AI Telegram Bot

Telegram Bot 客户端，支持角色扮演对话、文生图、TTS 语音等功能。

## 技术栈

- **框架**: python-telegram-bot 21.x
- **语言**: Python 3.11+
- **HTTP 客户端**: httpx
- **配置**: python-dotenv

## 目录结构

```
bot/
├── main.py                  # Bot 入口
├── config.py                # 配置管理
├── api_client.py            # Backend API 客户端
├── session.py               # 会话管理
├── user_binding.py          # 用户绑定
├── formatters.py            # 消息格式化
├── handlers/                # 命令处理器
│   ├── __init__.py
│   ├── commands.py          # 命令处理
│   ├── callbacks.py         # 回调处理
│   ├── messages.py          # 消息处理
│   ├── image_generation.py  # 文生图
│   ├── voice.py             # 语音/TTS
│   └── admin.py             # 管理员命令
└── .env                     # 环境变量
```

## 快速开始

### 1. 环境准备

```bash
# 使用与后端相同的 Python 环境
cd ../backend
source venv/bin/activate

# 安装 Bot 依赖 (与后端共用依赖)
```

### 2. 配置环境变量

```bash
cd ../bot
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
BACKEND_URL=http://localhost:8000/api

# 可选: 代理 (中国大陆需要)
TELEGRAM_PROXY_URL=socks5://127.0.0.1:7890
```

获取 Bot Token:
1. 在 Telegram 搜索 @BotFather
2. 发送 `/newbot` 创建新 Bot
3. 复制提供的 Token

### 3. 启动 Bot

```bash
# 从项目根目录启动
python -m bot.main

# 或从 bot 目录启动
cd bot
python -m bot.main
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `/start` | 开始使用，自动创建 Web 账户 |
| `/help` | 显示帮助信息 |
| `/role` | 选择/切换角色 |
| `/clear` | 清空当前对话历史 |
| `/status` | 查看当前角色状态 |
| `/image` | 生成场景图片 |
| `/profile` | 查看个人信息和积分余额 |
| `/tts` | 语音开关 |
| `/voice` | 设置角色声音克隆 |

## 功能特性

### 多用户支持
- 每个 Telegram 用户拥有独立会话
- 状态和历史记录互不干扰
- 支持同时与不同角色对话

### Web 账户绑定
- 首次使用 `/start` 自动创建 Web 账户
- 用户名格式: `tg_<telegram_id>`
- 用户中心显示 Web 端登录信息

### 快捷按钮
每次 AI 回复后显示快捷按钮:
- 🖼️ **/image** - 快速生成场景图片
- 📊 **/status** - 查看当前状态

### 积分系统
- 实时显示余额
- 消费前确认
- 与 Web 端共享积分

## 开发指南

### 添加新命令

1. 在 `handlers/commands.py` 添加处理函数:

```python
async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """新命令说明"""
    await update.message.reply_text("命令响应")
```

2. 在 `main.py` 注册:

```python
from bot.handlers.commands import new_command

application.add_handler(CommandHandler("newcmd", new_command))
```

### 调用后端 API

```python
from bot.api_client import api_client

# GET 请求
roles = await api_client.get_roles(tg_user_id)

# POST 请求
message = await api_client.send_message(tg_user_id, role_id, content)
```

### 发送消息

```python
await update.message.reply_text(
    "消息内容",
    parse_mode="Markdown",
    reply_markup=reply_markup
)
```

## 会话管理

Bot 使用内存存储会话状态:
- 当前角色
- 聊天历史
- TTS 开关
- 等待输入状态

## 部署

### 本地运行

```bash
# 使用 screen/tmux 保持运行
screen -S nyx-bot
python -m bot.main
# Ctrl+A+D 分离
```

### Docker

```bash
cd ..
docker-compose up -d
```

### 生产环境建议

- 使用 systemd 服务管理
- 配置日志轮转
- 监控 Bot 状态

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| TELEGRAM_BOT_TOKEN | 是 | - | BotFather 提供的 Token |
| BACKEND_URL | 是 | - | 后端 API 地址 |
| TELEGRAM_PROXY_URL | 否 | - | SOCKS5/HTTP 代理 |

## 故障排查

### Bot 无响应
1. 检查 Token 是否正确
2. 检查网络连接
3. 查看日志输出

### 无法连接后端
1. 确认后端服务已启动
2. 检查 BACKEND_URL 配置
3. 测试网络连通性

### 代理问题
中国大陆用户需要配置代理:
```env
TELEGRAM_PROXY_URL=socks5://127.0.0.1:7890
```
