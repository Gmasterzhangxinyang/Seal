# 文档核验自动盖章机器人

> **课程项目 MEC202 · SPECIFIC GENERAL PROJECT 9**  
> A robot server for self service of documentation  
> 指导老师：Bangxiang Chen（Bangxiang.chen@xjtlu.edu.cn）  
> 维护分支：`wene` · 最后更新：2026-05-16

---

## 目录

1. [项目简介](#1-项目简介)
2. [远程部署架构](#2-远程部署架构)
3. [系统架构（lxx 分支）](#3-系统架构lxx-分支)
4. [完整机器流程](#4-完整机器流程)
5. [功能清单](#5-功能清单)
6. [硬件说明](#6-硬件说明)
7. [软件环境与安装](#7-软件环境与安装)
8. [快速启动](#8-快速启动)
9. [远程连接方案](#9-远程连接方案)
10. [部署与更新流程](#10-部署与更新流程)
11. [Hermes 微信通知接入](#11-hermes-微信通知接入)
12. [API 文档](#12-api-文档)
13. [项目文件结构](#13-项目文件结构)
14. [配置说明](#14-配置说明)
15. [端口映射速查](#15-端口映射速查)
16. [故障排查](#16-故障排查)
17. [团队分工与时间线](#17-团队分工与时间线)
18. [采购清单](#18-采购清单)
19. [AI 开发助手（API 接入）](#19-ai-开发助手api-接入)

---

## 1. 项目简介

本项目构建一个基于 WeArm 六自由度机械臂的**文档核验自动盖章系统**。用户将 A4 文档放入摄像头下方 → 系统 OCR 识别文档内容 → 按模板规则核验 → 审核通过后机械臂自动盖章 → 生成审计日志。对无法自动核验的文件，系统自动生成人工复审队列。

### 关键能力

- **智能文档核验**：OCR 识别 + 规则引擎验证，支持自定义模板和字段提取
- **机器人自动盖章**：WeArm 六自由度机械臂精准定位盖章
- **审计追溯**：每次盖章生成结构化日志，含时间、操作员、文档类型、盖章前后照片
- **人工复审闭环**：自动核验失败时创建复审队列，管理员可查看文档照片后批准/拒绝
- **权限系统**：角色隔离（管理员、操作员、复审员），JWT/session 认证
- **远程部署**：Nginx + WireGuard 实现公网访问与本地硬件分离

### 用户角色

| 角色 | 职责 |
|------|------|
| 管理员 | 系统全局、管理用户、升级降级角色、查看全部日志 |
| 操作员 | 日常盖章操作、提交文件扫描 |
| 复审员 | 人工复审自动核验失败的文件 |

---

## 2. 远程部署架构

```
用户浏览器 / 微信小程序
        │
        ▼
┌─────────────────────────────────────────┐
│  云服务器 (XXXXXXX)               │
│  Ubuntu 24.04                            │
│                                          │
│  Nginx :80                               │
│  ├─ /          → 前端静态文件             │
│  ├─ /api/*     → WireGuard 代理          │
│  ├─ /api/stamp/leave → SSE 流式         │
│  └─ /video_feed → MJPEG 视频流          │
│                                          │
│  前端: /var/www/mec202-web/              │
│  源码: /home/ubuntu/MEC202/              │
└──────────────┬──────────────────────────┘
               │ WireGuard VPN
               │ 10.66.66.1 ⇄ 10.66.66.2
               ▼
┌─────────────────────────────────────────┐
│  机器人机器 (Windows)                     │
│                                          │
│  FastAPI :5001                           │
│  ├─ /api/stamp          盖章            │
│  ├─ /api/stamp/leave     SSE 流式盖章   │
│  ├─ /api/voice/*        语音控制        │
│  ├─ /api/calibration     标定           │
│  ├─ /api/logs            审计日志       │
│  ├─ /api/review/*        复审           │
│  └─ /video_feed          摄像头视频流   │
│                                          │
│  硬件: WeArm 机械臂 + USB摄像头          │
└─────────────────────────────────────────┘
```

---

## 3. 系统架构（lxx 分支）

### 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + Vite + TypeScript + TailwindCSS + shadcn/ui + Zustand |
| 后端 | FastAPI + SQLAlchemy + MySQL |
| OCR | GLM-4V（最新）/ PaddleOCR（备用） |
| 硬件 | WeArm 串口机械臂 |
| 视觉 | OpenCV + 二维码扫描 |
| 通知 | Hermes Agent Webhook → 微信 |
| 构建 | Turborepo monorepo + pnpm workspace |

### 数据流

```
摄像头拍照 → QR 扫描提取编号 → GLM-4V OCR 识别字段
  → 规则引擎验证（必填字段、类型、格式）
  → [通过] → 机械臂盖章 → 保存审计日志
  → [失败] → 创建人工复审队列 → 复审通过 → 盖章
```

---

## 4. 完整机器流程

```
① 操作员将 A4 文件平放到摄像头下
② 前端点击"扫描文件"
③ 摄像头拍照，OCR 识别文档内容
④ 调用模板规则验证：
   ✓ 自动通过 → 实时视频可见：机器人抓取印章、移动到位置、按压盖章
   ✗ 自动拒绝 → 提交"人工复审"队列，审核员复核后二次处理
⑤ 保存盖章前后照片和操作日志
⑥ 操作员取走文件
```

---

## 5. 功能清单

### 已完成

- [x] React SPA + FastAPI 前后端分离
- [x] JWT/Cookie 双认证 + 权限控制
- [x] PaddleOCR（旧）→ GLM-4V（新）文档内容识别
- [x] 二维码扫描提取编号
- [x] 自定义模板系统 + 规则引擎
- [x] 机械臂标定与逆运动学盖章
- [x] 手柄示教 + 动作录制/回放
- [x] MJPEG 实时视频流
- [x] 审计日志 + 图片归档
- [x] 人工复审工作流
- [x] 请假条 SSL 流式盖章
- [x] 语音控制（ASR + TTS）
- [x] 远程部署（Nginx + WireGuard + SSE）

---

## 6. 硬件说明

### WeArm 机械臂（当前硬件）

- 6 个串行总线舵机，基于 ST3215 协议（问读 7 字节、答 10 字节）
- 串口连接，波特率 115200
- 支持角度控制（0°–240°）和位置控制
- 末端安装印章夹具

### 摄像头

- USB 免驱摄像头，1080P
- 自动曝光、自动白平衡
- 支持 MSMF/DSHOW 双后端自动适配（Windows）

---

## 7. 软件环境与安装

### 环境要求

| 组件 | 版本 |
|------|------|
| Python | ≥ 3.11 |
| Node.js | ≥ 18 |
| pnpm | ≥ 9 |
| MySQL | ≥ 8.0 |

### 安装

```bash
git clone https://github.com/Gmasterzhangxinyang/MEC202
cd MEC202

# 前端
pnpm install

# 后端
cd apps/backend
pip install -r requirements.txt
# 或使用 uv：uv sync

# 数据库
# 启动 MySQL，创建 stamp_robot 库
alembic upgrade head
```

---

## 8. 快速启动

### 方式一：Turborepo（推荐）

```bash
pnpm dev     # 同时启动前端 Vite + 后端 Uvicorn
```

### 方式二：手动启动

```bash
# 终端 1：后端
cd apps/backend
uvicorn main:app --host 0.0.0.0 --port 5001 --reload

# 终端 2：前端
cd apps/web
pnpm dev
```

### 方式三：Windows 脚本

```bat
start_dev.bat
```

### 访问地址

- 前端：http://127.0.0.1:5173
- 后端 API：http://127.0.0.1:5001
- Swagger 文档：http://127.0.0.1:5001/docs
- 生产环境：http://XXXXXXX

### 演示账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 操作员 | operator | operator123 |
| 复审员 | reviewer | reviewer123 |

---

## 9. 远程连接方案

### 9.1 WireGuard VPN 隧道

**云服务器侧 (`/etc/wireguard/wg0.conf`)：**
```ini
[Interface]
PrivateKey = <云服务器私钥>
Address = 10.66.66.1/24
ListenPort = 51820

[Peer]
PublicKey = <机器人机器公钥>
AllowedIPs = 10.66.66.2/32
```

**机器人机器侧（Windows WireGuard 客户端）：**
```ini
[Interface]
PrivateKey = <机器人机器私钥>
Address = 10.66.66.2/24

[Peer]
PublicKey = <云服务器公钥>
Endpoint = XXXXXXX:51820
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
```

```bash
# 启动
sudo wg-quick up wg0
ping 10.66.66.2   # 验证连通
```

### 9.2 安全组（腾讯云控制台）

| 端口 | 协议 | 方向 | 说明 |
|------|------|------|------|
| 51820 | UDP | 入站 | WireGuard |
| 80 | TCP | 入站 | HTTP 前端 |

### 9.3 Nginx 反向代理

配置文件：`/etc/nginx/sites-enabled/mec202`

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/mec202-web;
    index index.html;

    # React SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 通用 API 代理
    location /api/ {
        proxy_pass http://10.66.66.2:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # SSE 流式盖章
    location /api/stamp/leave {
        proxy_pass http://10.66.66.2:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;
    }

    # 视频流
    location /video_feed {
        proxy_pass http://10.66.66.2:5001;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    location /api/cameras/video_feed {
        proxy_pass http://10.66.66.2:5001;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

---

## 10. 部署与更新流程

### 10.1 前端部署（云服务器）

```bash
cd /home/ubuntu/MEC202
git pull origin lxx

cd apps/web
pnpm install && pnpm build

sudo cp dist/index.html /var/www/mec202-web/
sudo cp -r dist/assets/* /var/www/mec202-web/assets/
sudo nginx -s reload
```

### 10.2 后端更新（机器人机器）

```bash
cd MEC202
git pull origin lxx
pip install -r requirements.txt   # 或 uv sync
# 检查 .env 配置
# 重启后端: uvicorn main:app --host 0.0.0.0 --port 5001
```

---

## 11. Hermes 微信通知接入

将 Hermes Agent 作为统一通知出口：审核/复审/盖章等事件 → Hermes Webhook → 微信通知。

### 事件类型

| 事件 | 触发时机 |
|------|----------|
| `REVIEW_CREATED` | 新的人工复审到达 |
| `REVIEW_RESOLVED` | 复审已批准或拒绝 |
| `AUDIT_APPROVED` | 自动审核通过并盖章 |
| `AUDIT_REJECTED` | 自动审核拒绝 |
| `STAMP_COMPLETED` | 盖章完成 |
| `SYSTEM_ERROR` | 摄像头/OCR/机械臂异常 |

### Hermes 侧配置

```bash
hermes gateway setup     # 启用 Webhooks + Weixin

hermes webhook subscribe mec202-review \
  --deliver weixin \
  --deliver-only \
  --prompt "【MEC202 盖章机器人】
事件：{event} | 状态：{status} | 文档：{doc_type}
操作员：{operator_id} | 复审ID：{review_id}
时间：{timestamp}
消息：{message}
详情：{detail}" \
  --description "MEC202 审核和复审通知"

# 测试
hermes webhook test mec202-review --payload '{
  "event":"REVIEW_CREATED","status":"pending",
  "doc_type":"leave","operator_id":"operator1",
  "review_id":1,"message":"新的请假条需要人工复审",
  "detail":"日期超过90天"
}'
```

### MEC202 后端接入

新增 `apps/backend/notification/hermes_client.py`：

```python
import logging, requests
from datetime import datetime

logger = logging.getLogger(__name__)

def notify_event(event: str, **kwargs) -> bool:
    from config import HERMES_NOTIFY_ENABLED, HERMES_WEBHOOK_URL
    if not HERMES_NOTIFY_ENABLED or not HERMES_WEBHOOK_URL:
        return False
    payload = {'event': event, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), **kwargs}
    try:
        r = requests.post(HERMES_WEBHOOK_URL, json=payload, timeout=2)
        if r.status_code >= 400:
            logger.warning('Hermes 通知失败: status=%s', r.status_code)
            return False
        return True
    except Exception as e:
        logger.warning('Hermes 通知异常: %s', e)
        return False
```

在 `config.py` 中添加环境变量：
```python
HERMES_NOTIFY_ENABLED = os.getenv('HERMES_NOTIFY_ENABLED', 'false').lower() == 'true'
HERMES_WEBHOOK_URL = os.getenv('HERMES_WEBHOOK_URL', '')
```

> ⚠️ 通知失败不能阻塞主业务流程。

---

## 12. API 文档

FastAPI 自动生成交互式文档：http://127.0.0.1:5001/docs

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/register` | 邮箱注册 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前用户 |
| GET | `/api/users` | 用户列表（管理员） |
| DELETE | `/api/users/{username}` | 删除用户（管理员） |
| POST | `/api/stamp` | 触发盖章 |
| POST | `/api/stamp/leave` | SSE 流式盖章 |
| GET | `/api/cameras` | 摄像头列表 |
| GET | `/api/cameras/video_feed` | MJPEG 视频流 |
| GET | `/api/logs` | 审计日志 |
| GET | `/api/review/pending` | 待复审列表 |
| POST | `/api/review/{id}/resolve` | 处理复审 |
| GET | `/api/templates` | 模板列表 |
| POST | `/api/templates` | 创建模板 |
| PUT | `/api/templates/{id}` | 更新模板 |
| DELETE | `/api/templates/{id}` | 删除模板 |
| GET | `/api/templates/{id}/export` | 导出模板 JSON |
| GET | `/api/stats/data` | 统计数据 |
| POST | `/api/calibration/move_single` | 舵机控制 |
| GET | `/api/calibration/config` | 标定配置 |
| POST | `/api/voice/chat` | 语音控制 |
| POST | `/api/voice/asr` | 语音识别 |
| POST | `/api/voice/tts` | 语音合成 |

---

## 13. 项目文件结构

```
MEC202/
├── apps/
│   ├── backend/
│   │   ├── api/              # FastAPI 路由
│   │   │   ├── main.py       # SPA 挂载 + 主要 API
│   │   │   ├── stamp.py      # 盖章流程 + SSE 流式
│   │   │   ├── voice.py      # 语音控制
│   │   │   ├── review.py     # 人工复审
│   │   │   ├── templates.py  # 模板 CRUD
│   │   │   ├── calibration.py
│   │   │   ├── logs.py
│   │   │   ├── stats.py
│   │   │   └── users.py
│   │   ├── database/         # SQLAlchemy 模型 + 迁移
│   │   ├── vision/           # OCR + QR + 摄像头
│   │   ├── hardware/         # WeArm 控制
│   │   ├── validator/        # 规则引擎
│   │   ├── integration/      # 外部集成
│   │   ├── config.py
│   │   └── main.py           # 应用入口
│   └── web/                  # React 前端
│       └── src/
│           ├── pages/
│           ├── components/
│           ├── stores/
│           └── lib/
├── doc/                      # 项目文档
├── pnpm-workspace.yaml
└── turbo.json
```

---

## 14. 配置说明

`apps/backend/config.py` 关键配置：

```python
ARM_TYPE = 'wearm'            # 机械臂类型
SIMULATION_MODE = False       # 仿真模式（无硬件时 True）

# 摄像头和串口自动检测，无需手动
# 如需手动指定：
# CAMERA_INDEX = 2
# SERIAL_PORT = 'COM9'

# 数据库
DB_HOST = 'localhost'
DB_PORT = 3306
```

---

## 15. 端口映射速查

| 服务 | 位置 | 端口 | 说明 |
|------|------|------|------|
| Nginx 前端 | 云服务器 | 80 | 对外访问入口 |
| FastAPI 后端 | 机器人机器 | 5001 | 经 WireGuard 代理 |
| WireGuard | 云服务器 | 51820/UDP | VPN 隧道 |
| Hermes Webhook | 云服务器 | 8644 | 内部通知 |
| Vite Dev | 本地 | 5173 | 开发热重载 |

---

## 16. 故障排查

### 前端 502
```bash
ping 10.66.66.2                        # WireGuard 是否连通
curl http://10.66.66.2:5001/api/health  # 后端是否运行
sudo wg show                            # 检查 VPN 状态
```

### SSE 流式无响应
确认 Nginx 中 `/api/stamp/leave` 包含：
```nginx
proxy_buffering off;
proxy_http_version 1.1;
chunked_transfer_encoding on;
```

### 视频流卡顿
确认 `proxy_buffering off` + `proxy_read_timeout 3600s`。

### 微信通知不送达
```bash
hermes webhook test mec202-review --payload '{...}'
hermes gateway status
```

### 摄像头黑屏
检查摄像头是否被其他程序占用。MSMF/DSHOW 自动适配已在 config.py 中实现。

### 找不到机械臂串口
系统自动检测 CH340 芯片。确认设备管理器中有 `USB-SERIAL CH340`。

### OCR 识别率低
在网页端 `模板管理` 中编辑对应模板的 `ocr_pattern` 正则。

---

## 17. 团队分工与时间线

| 成员 | 负责模块 | 核心交付 |
|------|---------|---------|
| 硬件 | 框架搭建 + 机械臂调试 | 准确盖章，自动标定 |
| 视觉 | OCR + 摄像头 + 分类 | 字段提取准确率 ≥ 90% |
| 逻辑 | 验证规则 + 模板系统 | 模板 CRUD + 动态提取 |
| 前端 | React SPA + API 对接 | 全功能页面，摄像头正常 |
| 集成 | API 层 + 主流程 + 联调 | 全流程端到端跑通 |

```
Week 1  采购硬件 → 搭KT板框架 → 接线 + 环境搭建
Week 2  OCR 真实表单测试 + 模板系统 + 机械臂调参
Week 3  React SPA 完成 + FastAPI API 层完成
Week 4  集体联调，全流程端到端测试
Week 5  用真实表单反复测试，修 bug
Week 6  演示准备，录制视频，撰写报告
```

---

## 18. 采购清单

| # | 淘宝搜索词 | 规格 | 预估价 |
|---|-----------|------|--------|
| 1 | `Arduino Uno R3 开发板 官方兼容` | 套餐含USB线 | ~40¥ |
| 2 | `MG996R 舵机 金属齿轮` | 1个 | ~25¥ |
| 3 | `MG90S 微型舵机` | 1个 | ~15¥ |
| 4 | `1080P USB摄像头 免驱 广角` | 免驱即插即用 | ~60¥ |
| 5 | `光敏印章 自动回墨 定制刻字` | 刻"已审核"，直径4cm | ~25¥ |
| 6 | `KT板 A3 白色 5mm` | 3-5张 | ~15¥ |
| 7 | `热熔胶枪 套装` | 含胶棒 | ~20¥ |
| 8 | `杜邦线 公对母 20cm 40根` | 1包 | ~8¥ |
| | | **总计** | **~208¥** |

---

*Turborepo Monorepo · Python FastAPI · React 19 · GLM-4V · WeArm · WireGuard*

---

## 19. AI 开发助手（API 接入）

云服务器上运行了一个 AI 编码助手，可通过 OpenAI 兼容 API 连接，帮助团队成员理解和修改服务端代码。

### 连接信息

```
Base URL:  http：//URL
API Key:   814988d70d320f23cf1dff306e9a8249abcfffaa39459a1f65486d1806522938
Model:     deepseek-v4-pro
```

### 方式一：OpenAI 兼容客户端（推荐）

支持 OpenWebUI、ChatBox、Continue (VS Code) 等任何兼容 OpenAI API 的工具。填入上面的 Base URL 和 API Key 即可。

### 方式二：curl

```bash
curl -X POST http：//URL \
  -H "Authorization: Bearer XXXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-pro",
    "messages": [{"role": "user", "content": "帮我看看 backend/main.py 的路由结构"}]
  }'
```

### 方式三：Python

```python
import requests

resp = requests.post(
    "http：//URL",
    headers={"Authorization": "Bearer XXXXXXXXX"},
    json={
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "解释 kinematics.py 里的逆运动学实现"}]
    }
)
print(resp.json()["choices"][0]["message"]["content"])
```

### 能力范围

- 阅读和解释 MEC202 源代码
- 搜索文件、函数和代码模式
- 帮助调试构建错误和配置问题
- 解释项目架构、API 端点和部署设置
- 修改 `/home/ubuntu/MEC202/` 下的服务端文件

### 限制

- 仅回答 MEC202 项目相关问题
- 文件操作限定在 `/home/ubuntu/MEC202/` 内
- 非项目问题会被拒绝回复
