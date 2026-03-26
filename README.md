# Nyx AI - 智能角色扮演系统

Nyx AI 是一个包含后端、Web 前端与 Telegram Bot 的完整应用，支持角色扮演对话、角色状态管理、文生图与语音生成，并带有积分消耗体系。

## 功能特性
- 用户系统：注册、登录、用户中心、统计
- 角色管理：创建/编辑/删除、公开/私密、系统预设角色
- 状态系统：可配置角色状态，聊天中实时更新
- AI 对话：上下文连续对话
- 文生图：基于对话生成图片（异步任务）
- TTS 语音：Web 与 Telegram 双端语音生成
- 积分系统：聊天/文生图/TTS/创建角色消耗
- Telegram Bot：多用户独立会话、快捷命令与按钮

## 技术栈
- 后端：FastAPI + SQLModel + SQLite
- 前端：Next.js 15 + React + TypeScript + Tailwind CSS + shadcn/ui
- Bot：python-telegram-bot
- LLM：OpenRouter / OpenAI / xAI Grok
- 文生图：Z-Image API
- 语音：Fish Audio API

## 目录结构
```
NyxAI_Tg/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── routers/         # API 路由
│   │   ├── models/          # SQLModel 模型
│   │   ├── services/        # 业务逻辑
│   │   ├── templates/admin/ # 管理后台模板 (Jinja2)
│   │   └── prompts/         # Prompt 模板
│   ├── requirements.txt
│   ├── create_admin.py      # 创建管理员
│   ├── create_default_role.py # 创建默认角色
│   └── create_system_roles.py # 创建系统预设角色
├── web-front/               # Next.js 前端
│   ├── app/                 # App Router 页面
│   ├── components/          # React 组件
│   ├── lib/                 # API 封装 & 状态管理
│   └── package.json
├── bot/                     # Telegram Bot
│   ├── main.py
│   ├── config.py
│   ├── api_client.py        # Backend API 客户端
│   └── handlers/            # 命令处理器
├── start_backend.sh         # 启动后端脚本
├── start_frontend.sh        # 启动前端脚本
└── start_bot.sh             # 启动 Bot 脚本
```

## 快速开始

### 1) 后端
```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

cd backend
cp .env.example .env
# 编辑 .env 填入 API Key

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

可选：创建管理员与默认角色
```bash
cd backend
python create_admin.py
python create_default_role.py
```

### 2) 前端
```bash
cd web-front
pnpm install
pnpm dev
# http://localhost:3000
```

### 3) Telegram Bot
```bash
cd bot
# 创建 bot/.env 并填写配置
python -m bot.main
```

## 环境变量

### backend/.env（示例）
- `SECRET_KEY` - JWT 密钥（生产环境必须修改）
- `DATABASE_URL` - SQLite 数据库地址
- `CORS_ORIGINS` - 前端地址白名单
- `OPENROUTER_API_KEY` / `OPENAI_API_KEY` - LLM API 密钥
- `ZIMAGE_API_KEY` - 文生图 API 密钥
- `FISH_AUDIO_API_KEY` - 语音合成 API 密钥
- `TELEGRAM_BOT_TOKEN` - Telegram Bot Token

### bot/.env（必需）
- TELEGRAM_BOT_TOKEN
- BACKEND_URL
- TELEGRAM_PROXY_URL（可选）

## 积分系统（默认消耗）
| 功能 | 消耗积分 |
|------|---------|
| 聊天 (chat) | 1 |
| 语音合成 (TTS) | 5 |
| 文生图 (TTI) | 10 |
| 创建角色 | 50 |
| AI 润色 | 10 |

## 主要接口
| 模块 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/auth/*` | 登录、注册、用户信息 |
| 角色 | `/api/roles/*` | 角色 CRUD、系统预设角色 |
| 聊天 | `/api/chat/*` | 发送消息、获取历史、状态管理 |
| 文生图 | `/api/chat/generate-image/*` | 异步图片生成任务 |
| TTS | `/api/chat/tts` | 语音合成 |
| 积分 | `/api/credits/*` | 积分查询、充值 |
| Bot | `/api/bot/*` | Telegram Bot 回调 |
| 管理后台 | `/admin/*` | SSR 管理界面（无需前端） |

访问 `http://localhost:8000/docs` 查看完整 Swagger 文档。

## Telegram Bot 支持命令
| 命令 | 说明 |
|------|------|
| `/start` | 开始使用，自动创建 Web 账户 |
| `/help` | 显示帮助信息 |
| `/role` | 选择/切换角色 |
| `/clear` | 清空当前对话历史 |
| `/status` | 查看当前角色状态 |
| `/image` | 生成场景图片 |
| `/profile` | 查看个人信息和积分 |
| `/tts` | 语音开关 |
| `/voice` | 设置角色声音克隆 |

## 说明
- 数据库存储在 `backend/instance/nyx_ai.db`
- Prompt 模板在 `backend/app/prompts/`，可直接修改

### 快捷按钮

每次 AI 回复后，消息下方会显示快捷按钮：
- 🖼️ **/image** - 快速生成场景图片
- 📊 **/status** - 查看当前状态

### 多用户支持

- 每个 Telegram 用户拥有独立的会话
- 状态和历史记录互不干扰
- 支持同时与不同角色对话

### Web 账户绑定

- 首次使用 `/start` 自动创建 Web 账户
- 用户名格式：`tg_<telegram_id>`
- 用户中心显示 Web 端登录信息（用户名和密码）
- 可在 Web 端登录查看统计数据

## 扩展功能

项目设计为模块化架构，易于扩展：
- 添加新的角色属性
- 扩展状态类型
- 集成更多AI模型
- ~~添加用户认证系统~~ ✅ 已完成
- ~~增加对话历史存储~~ ✅ 已完成
- ~~接入更多文生图模型~~ ✅ 已完成（Z-Image）
- ~~添加更多 Telegram Bot 命令~~ ✅ 已完成
- ~~添加用户权限管理~~ ✅ 已完成（管理员后台）
- ~~添加用户头像上传功能~~ ✅ 已完成
- ~~添加 TTS 语音功能~~ ✅ 已完成
- ~~添加角色状态系统~~ ✅ 已完成
- ~~添加积分系统~~ ✅ 已完成

### 文生图技术实现（异步轮询架构 + 高阶画图控制）

### 架构对比
| 模式 | 阻塞式（旧） | 异步架构（新） |
|------|-------------|---------------|
| 后端行为 | 阻塞等待40秒 | 立即返回 task_id |
| 前端行为 | 等待响应 | 每2秒轮询状态 |
| 后端影响 | 阻塞其他请求 | 无阻塞（FastAPI 原生异步） |
| 超时处理 | 后端504错误 | 前端30次轮询后超时 |

### 生成流程（新架构）
1. **提取视觉关键词** - 调用 Grok 模型分析聊天记录
2. **构建终极 Prompt** - 根据角色画风拼接：`画风词 + appearance_tags + 动态场景`
3. **创建任务** - POST `/api/generate` 获取 task_id（立即返回）
4. **前端轮询** - 每2秒 GET `/api/tasks/<task_id>` 查询状态
5. **保存结果** - 任务成功后 POST `/api/messages/<id>/save-image`
6. **显示图片** - 前端动态 append 图片到消息气泡

### 画风 Prompt 预设词
| 画风 | 质量强化词 |
|------|-----------|
| Anime | `(masterpiece, best quality, ultra-detailed, anime style, flat color:1.2)` |
| Realistic | `(raw photo, masterpiece, best quality, hyperrealistic, 8k resolution, cinematic lighting, photorealistic:1.2)` |
| 3D | `(masterpiece, best quality, 3d render, octane render, unreal engine 5, volumetric lighting:1.2)` |

### 前端轮询代码
```javascript
const pollInterval = setInterval(function () {
    $.ajax({
        url: `/api/tasks/${taskId}`,
        success: function (response) {
            if (response.status === 'SUCCESS') {
                clearInterval(pollInterval);
                saveImageAndDisplay(msgId, response.image_url);
            } else if (response.status === 'FAILED') {
                clearInterval(pollInterval);
                alert('生成失败');
            }
        }
    });
}, 2000); // 每2秒轮询
```

## 项目架构说明

### 前后端分离架构

```
backend/                    # FastAPI 后端
├── app/
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接
│   ├── main.py             # FastAPI 入口
│   ├── models/             # SQLModel 模型
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑
│   ├── templates/admin/    # 管理后台 SSR 模板
│   └── prompts/            # Prompt 配置
└── requirements.txt

web-front/                  # Next.js 前端
├── app/                    # App Router 页面
│   ├── page.tsx            # 首页（角色发现）
│   ├── chat/[id]/          # 聊天页面
│   ├── character/[id]/     # 角色详情
│   ├── create/             # 创建角色
│   └── profile/            # 个人中心
├── components/             # React 组件
│   ├── ui/                 # shadcn/ui 组件
│   ├── auth-modal.tsx      # 登录/注册弹窗
│   ├── character-card.tsx  # 角色卡片
│   └── credits-dialog.tsx  # 积分确认弹窗
├── lib/
│   ├── api.ts              # API 封装
│   ├── store.ts            # Zustand 状态管理
│   └── utils.ts            # 工具函数
└── package.json

bot/                        # Telegram Bot
├── main.py                 # Bot 入口
├── config.py               # Bot 配置
├── .env                    # 独立环境变量
├── api_client.py           # Backend API 客户端
├── session.py              # 会话管理
├── user_binding.py         # 用户绑定
├── formatters.py           # 消息格式化
└── handlers/               # 命令处理器
```

### 扩展指南

**添加 Bot 新命令：**

1. 在 `bot/handlers/commands.py` 添加：
```python
async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("新命令响应")
```

2. 在 `bot/main.py` 注册：
```python
application.add_handler(CommandHandler("newcmd", new_command))
```

**添加后端 API：**

在 `backend/app/routers/` 目录添加新路由：
```python
# backend/app/routers/new_module.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/new", tags=["新模块"])

@router.post("/endpoint")
async def new_endpoint(current_user: User = Depends(get_current_user)):
    return {"success": True}
```

然后在 `backend/app/main.py` 注册路由。

**修改提示词：**

直接编辑 `backend/app/prompts/` 目录下的 Markdown 文件：
- `backend/app/prompts/roleplay_system.md` - 角色扮演系统提示词
- `backend/app/prompts/scene_analyzer.md` - 场景分析提示词
- `backend/app/prompts/visual_extractor.md` - 视觉词提取提示词
- `backend/app/prompts/image_generation.md` - 文生图配置
- `backend/app/prompts/voice_config.md` - 声音配置

修改后无需重启服务，下次调用自动生效（热更新）。

## 部署

生产环境建议使用：
- Uvicorn 作为 ASGI 服务器
- Nginx 作为反向代理
- Supervisor 管理进程
- 配置 HTTPS 证书

### 后端部署示例
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 前端部署示例
```bash
cd web-front
pnpm build
# 将 out/ 目录部署到 Nginx
```
