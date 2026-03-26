# Nyx AI Backend

FastAPI 后端服务，提供 RESTful API、管理后台和 WebSocket 支持。

## 技术栈

- **框架**: FastAPI 0.115.0
- **ORM**: SQLModel + SQLAlchemy 2.0
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **缓存**: Redis (可选)
- **认证**: JWT (Access Token + Refresh Token)
- **限流**: slowapi
- **监控**: Prometheus 指标
- **日志**: 结构化 JSON 日志

## 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLModel 数据模型
│   ├── routers/             # API 路由
│   ├── services/            # 业务逻辑
│   ├── core/                # 核心组件
│   │   ├── logger.py        # 结构化日志
│   │   ├── limiter.py       # API 限流
│   │   ├── cache.py         # Redis 缓存
│   │   └── metrics.py       # Prometheus 指标
│   ├── middleware/          # 中间件
│   │   ├── security.py      # 安全响应头
│   │   └── logging.py       # 请求日志
│   ├── admin/               # 管理后台
│   ├── templates/           # Jinja2 模板
│   └── prompts/             # AI Prompt 模板
├── instance/                # SQLite 数据库目录
├── logs/                    # 日志目录
├── requirements.txt
└── .env                     # 环境变量
```

## 快速开始

### 1. 环境准备

```bash
# 使用 Python 3.11
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填
SECRET_KEY=your-secret-key-here

# API Keys (至少配置一个 LLM)
OPENROUTER_API_KEY=your-openrouter-key
ZIMAGE_API_KEY=your-zimage-key
FISH_AUDIO_API_KEY=your-fish-audio-key

# 可选: Redis (用于生产环境)
REDIS_URL=redis://localhost:6379/0
```

### 3. 启动服务

```bash
# 开发模式 (热重载)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 初始化数据

```bash
# 创建管理员账号
python create_admin.py

# 创建默认角色
python create_default_role.py

# 创建系统预设角色
python create_system_roles.py
```

## API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## 主要接口

| 模块 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/auth/*` | 登录、注册、Token 刷新 |
| 角色 | `/api/roles/*` | 角色 CRUD、系统预设 |
| 聊天 | `/api/chat/*` | 对话、历史、状态管理 |
| 文生图 | `/api/chat/generate-image/*` | 异步图片生成 |
| TTS | `/api/chat/tts` | 语音合成 |
| 积分 | `/api/credits/*` | 积分查询、充值 |
| Bot | `/api/bot/*` | Telegram Bot 回调 |
| 监控 | `/metrics` | Prometheus 指标 |
| 管理后台 | `/admin/*` | SSR 管理界面 |

## 积分系统

| 功能 | 消耗积分 |
|------|---------|
| 聊天 | 1 |
| TTS 语音 | 5 |
| 文生图 | 10 |
| 创建角色 | 50 |
| AI 润色 | 10 |

## 安全特性

- API 限流 (slowapi)
- JWT 双令牌机制 (Access 2h + Refresh 7d)
- Token 黑名单 (Redis)
- 安全响应头 (CSP, HSTS, X-Frame-Options)
- 密码哈希 (bcrypt)
- 审计日志

## 生产部署

### Docker

```bash
cd ..
docker-compose up -d
```

### 手动部署

```bash
# 使用 systemd 或 supervisor 管理进程
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Nginx 反向代理配置见 ../nginx/nginx.conf
```

## 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| SECRET_KEY | 是 | - | JWT 密钥 |
| DATABASE_URL | 否 | sqlite:///./instance/nyx_ai.db | 数据库连接 |
| REDIS_URL | 否 | - | Redis 连接 |
| ACCESS_TOKEN_EXPIRE_MINUTES | 否 | 120 | Access Token 过期时间 |
| DEBUG | 否 | false | 调试模式 |
| OPENROUTER_API_KEY | 否* | - | LLM API |
| OPENAI_API_KEY | 否* | - | OpenAI API |
| ZIMAGE_API_KEY | 否 | - | 文生图 API |
| FISH_AUDIO_API_KEY | 否 | - | TTS API |

*至少配置一个 LLM API
