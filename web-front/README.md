# Nyx AI Web Frontend

Next.js 16 前端应用，提供角色扮演对话界面。

## 技术栈

- **框架**: Next.js 16.1.6 (App Router)
- **语言**: TypeScript 5.7
- **样式**: Tailwind CSS 4.2
- **组件**: shadcn/ui + Radix UI
- **状态管理**: Zustand 5
- **表单**: React Hook Form + Zod
- **包管理**: pnpm

## 目录结构

```
web-front/
├── app/                     # App Router
│   ├── page.tsx             # 首页 (角色发现)
│   ├── layout.tsx           # 根布局
│   ├── chat/[id]/           # 聊天页面
│   ├── character/[id]/      # 角色详情
│   ├── create/              # 创建角色
│   ├── edit/[id]/           # 编辑角色
│   ├── profile/             # 个人中心
│   └── settings/            # 设置
├── components/              # React 组件
│   ├── ui/                  # shadcn/ui 组件
│   ├── auth-modal.tsx       # 登录/注册弹窗
│   ├── character-card.tsx   # 角色卡片
│   ├── chat-message.tsx     # 聊天消息
│   ├── image-generator.tsx  # 文生图组件
│   └── credits-dialog.tsx   # 积分确认弹窗
├── lib/                     # 工具库
│   ├── api.ts               # API 封装
│   ├── store.ts             # Zustand 状态管理
│   └── utils.ts             # 工具函数
├── hooks/                   # 自定义 Hooks
├── public/                  # 静态资源
└── styles/                  # 全局样式
```

## 快速开始

### 1. 安装依赖

```bash
pnpm install
```

### 2. 配置环境变量

```bash
cp .env.example .env.local
```

编辑 `.env.local`：

```env
# API 地址
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### 3. 启动开发服务器

```bash
pnpm dev
```

访问 http://localhost:3000

### 4. 构建生产版本

```bash
pnpm build
```

输出目录: `out/`

## 开发指南

### 添加新页面

```typescript
// app/new-page/page.tsx
export default function NewPage() {
  return <div>新页面</div>;
}
```

### 添加 shadcn/ui 组件

```bash
npx shadcn add button
```

### API 调用示例

```typescript
import { api } from '@/lib/api';

// GET 请求
const roles = await api.getRoles();

// POST 请求
const message = await api.sendMessage(roleId, content);
```

### 状态管理示例

```typescript
import { useAppStore } from '@/lib/store';

const { user, setUser } = useAppStore();
```

## 页面说明

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `/` | 角色发现、搜索 |
| 聊天 | `/chat/[id]` | 与角色对话 |
| 角色详情 | `/character/[id]` | 查看角色信息 |
| 创建角色 | `/create` | 创建新角色 |
| 编辑角色 | `/edit/[id]` | 修改角色 |
| 个人中心 | `/profile` | 用户信息、统计 |
| 设置 | `/settings` | 应用设置 |

## 核心功能

### 角色扮演聊天
- 实时对话
- 上下文记忆
- 角色状态显示
- 快捷操作按钮

### 文生图
- 异步生成
- 轮询状态
- 图片预览
- 保存到聊天记录

### TTS 语音
- 文字转语音
- 角色声音克隆
- 语音预览

### 积分系统
- 余额显示
- 消费确认
- 充值入口

## 注意事项

1. **动态路由参数**: Next.js 15+ 需要使用 `use()` 解包 params
   ```typescript
   const { id } = use(params);
   ```

2. **客户端组件**: 使用浏览器 API 时需添加 `"use client"`

3. **API 代理**: 开发时自动代理到后端，生产需配置 Nginx

## 部署

### 静态导出

```bash
pnpm build
# 部署 out/ 目录到 CDN 或 Nginx
```

### Docker

```bash
cd ..
docker-compose up -d
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| NEXT_PUBLIC_API_URL | 否 | http://localhost:8000/api | 后端 API 地址 |
