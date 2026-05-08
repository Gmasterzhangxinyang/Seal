# 文档核验自动盖章机器人

> **课程项目 MEC202 · SPECIFIC GENERAL PROJECT 9**  
> A robot server for self service of documentation  
> 指导老师：Bangxiang Chen（Bangxiang.chen@xjtlu.edu.cn）

---

## 目录

1. [项目简介](#1-项目简介)
2. [系统架构](#2-系统架构)
3. [完整机器流程](#3-完整机器流程)
4. [功能清单](#4-功能清单)
5. [硬件说明](#5-硬件说明)
6. [软件环境与安装](#6-软件环境与安装)
7. [快速启动](#7-快速启动)
8. [正式运行（接硬件）](#8-正式运行接硬件)
9. [项目文件结构](#9-项目文件结构)
10. [API 文档](#10-api-文档)
11. [团队分工](#11-团队分工)
12. [开发时间线](#12-开发时间线)
13. [硬件组装指南](#13-硬件组装指南)
14. [配置说明](#14-配置说明)
15. [常见问题](#15-常见问题)
16. [采购清单](#16-采购清单)

---

## 1. 项目简介

本项目是一套**文档核验与自动盖章机器人系统**，面向学校行政场景，实现文档提交的全流程自动化：

- 操作员将申请表放入设备 → 系统自动扫描、识别、验证 → 通过则自动盖章，拒绝则给出具体原因
- 所有操作生成审计日志（含盖章前后对比图），全程可追溯
- 异常文件自动推入人工复审队列，由复审员在网页端处理

**核心价值：** 替代人工审核和手动盖章，减少行政负担，同时通过完整审计链保证合规性。

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React SPA)                      │
│   Vite + TypeScript + TailwindCSS + shadcn/ui           │
│   摄像头预览 / 操作台 / 模板管理 / 日志 / 复审 / 标定    │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP API / MJPEG Stream
┌───────────────────────▼─────────────────────────────────┐
│                 后端 API (FastAPI)                        │
│   RESTful JSON API · Pydantic 数据验证 · 自动 OpenAPI    │
└──┬────────────┬───────────────┬──────────────┬──────────┘
   │            │               │              │
   ▼            ▼               ▼              ▼
vision/      validator/      hardware/    integration/
摄像头拍照    规则验证引擎    机械臂控制     DMS上传
OCR识别       ID对库验证     逆运动学
二维码扫描    多页检测        自动标定
模板匹配      动态字段提取
                        │
              ┌─────────▼─────────┐
              │    database/      │
              │  SQLite 审计日志  │
              │  人工复审队列     │
              │  模板配置         │
              │  人员数据库       │
              └───────────────────┘
```

**技术栈：**

| 层 | 技术 |
|---|---|
| 前端 | React 19 + Vite + TypeScript + TailwindCSS v4 + shadcn/ui |
| 状态管理 | Zustand |
| 后端 | Python FastAPI |
| OCR | PaddleOCR（中文优化） |
| 数据库 | SQLite |
| 硬件 | WeArm 机械臂 (CH340 串口) / Hiwonder ArmPi (WiFi) |

---

## 3. 完整机器流程

```
① 操作员登录系统（Role: operator / admin）
       │
② 放入文件到对齐槽
       │
③ 点击网页"扫描 & 盖章"按钮
       │
④ 摄像头俯拍原始图 → 保存为 before_YYYYMMDD_HHMMSS.jpg
       │
⑤ 扫描二维码 / 条形码 → 识别文件类型
       │
⑥ PaddleOCR 全文识别 → 提取字段
       │
⑦ 根据模板 ocr_pattern 动态提取字段（支持自定义正则）
       │
⑧ 多页完整性检测
       │
⑨ 六项并行验证 → 通过/拒绝/推入复审
       │
⑩ 机械臂盖章（逆运动学求解盖章位置）
       │
⑪ 摄像头再次拍摄 → 审计日志写入
       │
⑫ 网页显示结果 → 操作员取走文件
```

---

## 4. 功能清单

| 功能 | 实现方式 | 状态 |
|------|---------|------|
| OCR字段提取 | PaddleOCR + 模板动态正则 | ✅ |
| 二维码/条形码扫描 | pyzbar + OpenCV | ✅ |
| 文件类型分类 | 二维码前缀 + 关键词评分 | ✅ |
| 动态模板字段提取 | 模板 ocr_pattern 配置 | ✅ |
| 模板导出/导入 | JSON 格式导出 | ✅ |
| 摄像头/串口自动检测 | VID:PID 匹配 + DSHOW 协商 | ✅ |
| 多页完整性检测 | OCR页码正则匹配 | ✅ |
| 必填字段验证 | 按文件类型配置规则 | ✅ |
| 日期合法性验证 | 格式检查 + 超期警告 | ✅ |
| 签名栏检测 | 关键词检索 | ✅ |
| ID号对库验证 | SQLite personnel表 | ✅ |
| 机械臂逆运动学 | 6轴IK求解 + 标定插值 | ✅ |
| 自动标定工具 | Web端四角标定 | ✅ |
| 审计日志（前后图） | SQLite + 文件系统 | ✅ |
| 人工复审队列 | Web页面 + 数据库 | ✅ |
| 角色权限控制 | operator/reviewer/admin | ✅ |
| DMS系统集成 | REST API客户端 | ✅ |
| 仿真模式（无硬件） | SIMULATION_MODE开关 | ✅ |

---

## 5. 硬件说明

### WeArm 机械臂（当前硬件）

| 项目 | 参数 |
|------|------|
| 型号 | WeArm（Arduino 控制） |
| 连接 | USB CH340 串口，自动检测 |
| 波特率 | 115200 |
| 电源 | 7.5V 3A |

### Hiwonder ArmPi（备选）

| 项目 | 参数 |
|------|------|
| 连接 | WiFi HTTP（树莓派中继） |
| 配置 | `ARM_TYPE = 'hiwonder'` |

通过 `config.py` 中 `ARM_TYPE` 切换：`'wearm'` 或 `'hiwonder'`。

---

## 6. 软件环境与安装

### 环境要求

- Python 3.10+
- Node.js 18+（前端开发）
- 内存：4GB+（PaddleOCR 模型加载需要约 1.5GB）

### 安装

```bash
# 克隆项目
cd MEC202

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install && cd ..

# 构建前端（生产模式）
cd frontend && npm run build && cd ..
```

### 依赖说明

**后端 (Python):**
```
fastapi + uvicorn       # Web API 框架
paddleocr + paddlepaddle # OCR 引擎
opencv-python            # 图像处理
pyserial                 # 串口通信（WeArm）
pyzbar                   # 二维码扫描
pillow + werkzeug        # 图像工具
```

**前端 (Node.js):**
```
react + react-router-dom  # SPA 框架
tailwindcss + shadcn/ui   # UI 组件
zustand                    # 状态管理
recharts                   # 图表
```

---

## 7. 快速启动

### 方式一：Makefile（推荐）

```bash
# 开发模式：同时启动前端和后端
make dev

# 或分开启动
make dev-backend   # FastAPI 后端 (端口 5001)
make dev-frontend  # Vite 前端 (端口 5173)

# 构建前端
make build

# 安装所有依赖
make install
```

### 方式二：手动启动

```bash
# 终端 1：启动后端
python -m api.main

# 终端 2：启动前端开发服务器
cd frontend && npm run dev
```

### 访问地址

| 模式 | 地址 |
|------|------|
| 开发 | http://localhost:5173（Vite 代理 API 到 5001） |
| 生产 | http://127.0.0.1:5001（FastAPI 直接服务前端） |

### 演示账号

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin123 | 管理员（全功能） |
| operator1 | op123 | 操作员 |
| reviewer1 | reviewer123 | 复审员 |

---

## 8. 正式运行（接硬件）

1. 连接 USB 摄像头和机械臂
2. 系统自动检测设备（无需手动配置 COM 口）
3. 启动服务：`make dev`
4. 打开浏览器，登录后使用操作台

摄像头和串口在启动时自动检测：
- 串口：通过 CH340 芯片 VID:PID 自动识别
- 摄像头：优先选择 DSHOW 后端的外部 USB 摄像头

---

## 9. 项目文件结构

```
MEC202/
├── Makefile                   # 一键启动/构建
├── config.py                  # 全局配置（自动检测设备）
├── main.py                    # 主流程编排
│
├── api/                       # FastAPI 后端
│   ├── main.py                # 应用入口
│   ├── deps.py                # 认证中间件
│   ├── auth.py                # 登录/登出
│   ├── stamp.py               # 盖章操作
│   ├── cameras.py             # 摄像头管理 + MJPEG 流
│   ├── logs.py                # 审计日志
│   ├── review.py              # 人工复审
│   ├── templates.py           # 模板 CRUD + 导出
│   ├── stats.py               # 统计数据
│   ├── calibration.py         # 机械臂标定
│   └── images.py              # 图片服务
│
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── App.tsx            # 路由配置
│   │   ├── pages/             # 页面组件
│   │   ├── components/        # UI 组件
│   │   │   ├── camera/        # 摄像头视频流
│   │   │   ├── layout/        # 导航布局
│   │   │   ├── stamp/         # 操作台组件
│   │   │   ├── templates/     # 模板编辑
│   │   │   └── calibration/   # 标定控制
│   │   ├── stores/            # Zustand 状态
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── lib/               # API 客户端
│   │   └── types/             # TypeScript 类型
│   └── vite.config.ts         # Vite 配置（开发代理）
│
├── database/                  # 数据层
│   ├── models.py              # 建表 + 预设模板
│   ├── audit.py               # 审计日志
│   ├── review_queue.py        # 复审队列
│   └── template.py            # 模板 CRUD
│
├── vision/                    # 视觉模块
│   ├── camera.py              # 摄像头控制（单例 + 帧缓冲）
│   ├── ocr.py                 # OCR + 动态模板提取
│   ├── classifier.py          # 文档自动分类
│   └── qr_scanner.py          # 二维码扫描
│
├── hardware/                  # 硬件控制
│   ├── arm.py                 # 机械臂工厂
│   ├── wearm.py               # WeArm 串口控制
│   ├── hiwonder.py            # Hiwonder WiFi 控制
│   └── kinematics.py          # 逆运动学求解
│
├── validator/                 # 验证规则
│   └── rules.py               # 规则引擎
│
└── integration/               # 外部集成
    └── dms_client.py          # DMS REST API
```

---

## 10. API 文档

FastAPI 自动生成交互式 API 文档：

- Swagger UI: http://127.0.0.1:5001/docs
- ReDoc: http://127.0.0.1:5001/redoc

### 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前用户 |
| POST | `/api/stamp` | 触发盖章流程 |
| GET | `/api/cameras` | 摄像头列表 |
| GET | `/api/cameras/video_feed` | MJPEG 视频流 |
| GET | `/api/cameras/paper_status` | 纸张检测状态 |
| GET | `/api/logs` | 审计日志 |
| GET | `/api/review/pending` | 待复审列表 |
| GET | `/api/templates` | 模板列表 |
| POST | `/api/templates` | 创建模板 |
| PUT | `/api/templates/{id}` | 更新模板 |
| GET | `/api/templates/{id}/export` | 导出模板 JSON |
| GET | `/api/stats/data` | 统计数据 |
| POST | `/api/calibration/move_single` | 舵机控制 |

---

## 11. 团队分工

| 成员 | 负责模块 | 核心文件 | 交付标准 |
|------|---------|---------|---------|
| **甲**（硬件） | 框架搭建 + 机械臂调试 | `hardware/` | 机械臂准确盖章，自动标定正常 |
| **乙**（视觉） | OCR识别 + 摄像头 + 分类 | `vision/` | 字段提取准确率 ≥ 90%，分类正确 |
| **丙**（逻辑） | 验证规则 + 模板系统 | `validator/` `database/template.py` | 模板 CRUD + 动态提取 |
| **丁**（前端） | React SPA + API 对接 | `frontend/` | 所有页面功能完整，摄像头不黑屏 |
| **戊**（集成） | API 层 + 主流程 + 联调 | `api/` `main.py` | 全流程端到端跑通 |

---

## 12. 开发时间线

```
Week 1  甲：采购硬件 → 搭KT板框架 → 接线
        乙丙丁戊：安装环境，跑通 PaddleOCR demo

Week 2  乙：用真实学校表单测试 OCR
        丙：完成模板系统和验证规则
        甲：调试机械臂角度

Week 3  丁：完成 React SPA 所有页面
        戊：完成 FastAPI API 层

Week 4  集体联调：全流程端到端测试

Week 5  用真实表单反复测试，修 bug

Week 6  准备演示，录制视频，撰写报告
```

---

## 13. 硬件组装指南

### 框架搭建（约2小时）

1. 裁 3 张 KT 板：底板（A3）、两块侧板（30cm×10cm）
2. 热熔胶粘侧板到底板两侧
3. 横梁跨过顶部，摄像头固定在中央（正对下方）
4. 底板上画 A4 矩形，粘 L 型挡板
5. 机械臂固定在侧板，调整盖章位置

### 标定

启动后在网页端 `机械臂标定` 页面操作：
1. 点击"测试连接"确认通信
2. 调整 6 个舵机到目标位置
3. 保存四角位置（TL/TR/BL/BR）
4. 测试移动确认准确

---

## 14. 配置说明

`config.py` 关键配置：

```python
# 机械臂类型
ARM_TYPE = 'wearm'            # 'wearm' 或 'hiwonder'

# 摄像头和串口自动检测，无需手动配置
# 如果需要手动指定：
# CAMERA_INDEX = 2
# SERIAL_PORT = 'COM9'

# 仿真模式（无硬件时设 True）
SIMULATION_MODE = False
```

### 添加人员数据

```python
import sqlite3
conn = sqlite3.connect('stamp_robot.db')
conn.execute("INSERT INTO personnel VALUES ('20210099', '你的名字', '计算机学院', 'student')")
conn.commit()
```

---

## 15. 常见问题

**Q: `make dev` 启动失败？**  
A: 确保已运行 `make install` 安装所有依赖。

**Q: 摄像头黑屏？**  
A: SPA 架构下摄像头流始终保持连接。如果仍有问题，检查摄像头是否被其他程序占用。

**Q: 找不到机械臂串口？**  
A: 系统自动检测 CH340 芯片。确认设备管理器中能看到 `USB-SERIAL CH340`。插拔后可能变更 COM 口，但系统会自动重新检测。

**Q: OCR 识别率低？**  
A: 在网页端 `模板管理` 中编辑对应模板的 `ocr_pattern` 正则，无需修改代码。

**Q: 如何添加新的文件类型？**  
A: 在 `模板管理` 页面新建模板，配置关键词、正则和字段定义即可。

---

## 16. 采购清单

| # | 淘宝搜索词 | 规格要求 | 预估价 |
|---|-----------|---------|--------|
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

*项目使用 Python 3.10+ / FastAPI / React / PaddleOCR / SQLite*
