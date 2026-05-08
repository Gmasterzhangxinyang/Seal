# 前后端分离重构方案

## Context

当前前端存在三个核心问题：
1. **摄像头黑屏** — 传统 MPA 架构，页面切换时 `<img src="/video_feed">` 被销毁，MJPEG 流断开需重连
2. **摄像头初始化慢** — `config.py` 导入时逐个打开 10 个摄像头检测，耗时约 8 秒
3. **页面切换体验差** — 每次导航整页刷新，JS/CSS/视频流全部重建

## 技术选型

| 层 | 技术 | 理由 |
|---|---|---|
| 前端 | React + Vite + TypeScript + TailwindCSS v4 + shadcn/ui | 用户选择，后续功能扩展方便 |
| 状态管理 | Zustand | 轻量，本项目状态简单 |
| 图表 | Recharts | React 声明式 API，替代 chart.js |
| 后端 | Python FastAPI | 原生 async、自动 OpenAPI 文档、Pydantic 数据验证、比 Flask 更现代 |
| 认证 | Session Cookie（通过 fastapi-session 或中间件） | 单机部署，简单可靠 |

## 摄像头黑屏核心解决方案

将 `<img src="/video_feed">` 放在 AppShell 层级，始终挂载、永不卸载。操作台页面通过 CSS `display:none` 切换可见性，路由切换时 MJPEG 流不断开。

## 分阶段实施

### 阶段 0：前端脚手架
1. 在项目根目录创建 `frontend/`，Vite + React + TS 初始化
2. 安装依赖：tailwindcss, react-router-dom, zustand, recharts, lucide-react
3. 配置 TailwindCSS v4、shadcn/ui 组件
4. 配置 `vite.config.ts` 开发代理
5. 创建 `src/lib/api-client.ts` 封装 fetch（自动带 cookie、401 跳转）

### 阶段 1：后端 FastAPI 重写
将 Flask 替换为 FastAPI。**硬件层（hardware/）、视觉层（vision/）、数据库层（database/）完全不动。**

文件变更：
- 新增 `api/` 目录，按功能拆分路由：auth.py, stamp.py, cameras.py, logs.py, review.py, templates.py, stats.py, calibration.py, images.py
- 新增 `api/deps.py` — 依赖注入（认证、摄像头实例、处理器实例）
- 新增 `api/main.py` — FastAPI 应用入口，注册路由
- 删除 `web/app.py`（或标记为废弃）
- MJPEG 流改用 FastAPI 的 `StreamingResponse`

关键 API 路由（所有路由前缀 `/api`）：
| 旧 Flask 路由 | 新 FastAPI 路由 | 变化 |
|---|---|---|
| `POST /login` (form) | `POST /api/auth/login` (JSON) | Pydantic model |
| `GET /logs` (render) | `GET /api/logs` (JSON) | 改为 JSON |
| `GET /review` (render) | `GET /api/review/pending` + `/api/review/all` | 拆分 |
| `POST /admin/templates/new` (form) | `POST /api/templates` (JSON) | RESTful |
| `POST /admin/templates/<id>/edit` (form) | `PUT /api/templates/{id}` (JSON) | RESTful |
| `/video_feed` | `/api/video_feed` | StreamingResponse |

### 阶段 2：前端核心 — 操作台
解决摄像头黑屏的关键阶段。

核心文件：
- `src/components/camera/camera-feed.tsx` — MJPEG 流组件，始终挂载
- `src/components/layout/app-shell.tsx` — 导航 + 内容区 + 隐藏的持久摄像头
- `src/pages/stamp-page.tsx` — 操作台
- `src/pages/login-page.tsx` — 登录
- `src/stores/auth-store.ts` — Zustand 认证状态

摄像头持久化方案：
```
AppShell (始终挂载)
├── NavBar
├── <Outlet /> (路由内容区)
│   ├── StampPage (display:none 切换，不卸载)
│   └── 其他页面
└── CameraFeed (固定定位，非操作台时隐藏但保持连接)
```

### 阶段 3：日志与复审
- `src/pages/logs-page.tsx` + `src/components/logs/`
- `src/pages/review-page.tsx` + `src/components/review/`

### 阶段 4：模板管理
- `src/pages/templates-page.tsx`
- `src/pages/template-edit-page.tsx`
- `src/components/templates/field-editor.tsx` — 动态字段编辑

### 阶段 5：统计与标定
- `src/pages/stats-page.tsx` — Recharts 图表
- `src/pages/calibration-page.tsx` — 舵机滑块 + 四角标定

### 阶段 6：部署配置
- Vite 生产构建 → `frontend/dist/`
- FastAPI StaticFiles 服务前端
- 端到端测试

## 目录结构

```
MEC202/
├── frontend/                 # React 前端（新增）
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   └── utils.ts
│   │   ├── stores/
│   │   ├── hooks/
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui
│   │   │   ├── layout/
│   │   │   ├── camera/
│   │   │   ├── stamp/
│   │   │   ├── logs/
│   │   │   ├── review/
│   │   │   ├── templates/
│   │   │   ├── stats/
│   │   │   └── calibration/
│   │   ├── pages/
│   │   └── types/
│   └── vite.config.ts
├── api/                      # FastAPI 后端（新增）
│   ├── main.py               # FastAPI 应用入口
│   ├── deps.py               # 依赖注入
│   ├── auth.py               # 认证路由
│   ├── stamp.py              # 盖章操作
│   ├── cameras.py            # 摄像头管理 + MJPEG 流
│   ├── logs.py               # 审计日志
│   ├── review.py             # 人工复审
│   ├── templates.py          # 模板管理
│   ├── stats.py              # 统计
│   ├── calibration.py        # 标定
│   └── images.py             # 图片服务
├── database/                 # 不变
├── hardware/                 # 不变
├── vision/                   # 不变
├── validator/                # 不变
└── config.py                 # 不变
```

## 验证方式

1. 终端 1：`uvicorn api.main:app --port 5001`（FastAPI）
2. 终端 2：`cd frontend && npm run dev`（Vite 5173）
3. 浏览器访问 `http://localhost:5173`
4. 测试：登录 → 操作台视频流 → 页面切换 → 视频流无中断
5. 测试：盖章流程、模板 CRUD、标定、统计
