# 请假条核验自动盖章机器人

> **课程项目 MEC202 · SPECIFIC GENERAL PROJECT 9**  
> Leave Request Verification and Auto-Stamping Robot  
> A robot server for self service of documentation  
> 指导老师：Bangxiang Chen（Bangxiang.chen@xjtlu.edu.cn）

---

## 目录

1. [项目简介](#1-项目简介)
2. [核心业务场景](#2-核心业务场景)
3. [系统架构](#3-系统架构)
4. [完整业务流程](#4-完整业务流程)
5. [核验逻辑与决策机制](#5-核验逻辑与决策机制)
6. [功能清单](#6-功能清单)
7. [数据库设计](#7-数据库设计)
8. [后端 API 设计](#8-后端-api-设计)
9. [前端页面设计](#9-前端页面设计)
10. [请假条模板与 OCR 字段抽取](#10-请假条模板与-ocr-字段抽取)
11. [机械臂盖章与安全控制](#11-机械臂盖章与安全控制)
12. [Superpower 分阶段开发方案](#12-superpower-分阶段开发方案)
13. [最终验收标准](#13-最终验收标准)
14. [软件环境与安装](#14-软件环境与安装)
15. [快速启动](#15-快速启动)
16. [正式运行：接硬件](#16-正式运行接硬件)
17. [项目文件结构](#17-项目文件结构)
18. [团队分工](#18-团队分工)
19. [开发时间线](#19-开发时间线)
20. [硬件组装指南](#20-硬件组装指南)
21. [配置说明](#21-配置说明)
22. [常见问题](#22-常见问题)
23. [采购清单](#23-采购清单)
24. [给 Claude Code 的改造任务说明](#24-给-claude-code-的改造任务说明)

---

## 1. 项目简介

本项目是一套面向学校行政场景的**请假条核验自动盖章机器人系统**。

系统采用“线上申请 + 二维码绑定 + 线下扫描核验 + 自动盖章 + 审计留痕”的流程：学生先在网页端提交请假申请，管理员或老师审批通过后，系统生成唯一申请编号和防篡改二维码。学生将带二维码的纸质请假条带到线下设备，机器人通过摄像头扫描二维码并 OCR 识别纸质请假条内容，将纸质内容与线上申请记录进行比对，只有验证通过后才允许机械臂自动盖章。

本项目不再只判断“这张纸像不像请假条”，而是判断：

> 这张纸质请假条是否对应系统中真实存在、已经审批通过、尚未盖章，并且内容一致的线上请假申请。

**核心价值：**

- 防止伪造请假条被盖章。
- 防止未审批申请被线下盖章。
- 防止同一申请重复盖章。
- 降低人工审核和手动盖章负担。
- 通过 OCR 结果、验证结果、盖章前后图片和操作日志实现全流程可追溯。

---

## 2. 核心业务场景

### 2.1 用户角色

| 角色 | 权限 |
|---|---|
| 学生 | 在线提交请假申请，查看申请状态，下载或打印带二维码的请假条 |
| 操作员 operator | 在线下设备上扫描请假条，触发核验与盖章流程 |
| 复审员 reviewer | 处理系统无法自动判断的 REVIEW 任务 |
| 管理员 admin | 管理用户、模板、申请、审批、复审、日志和系统配置 |

### 2.2 请假申请状态

| 状态 | 含义 |
|---|---|
| `SUBMITTED` | 学生已提交，等待审批 |
| `APPROVED` | 审批通过，等待线下盖章 |
| `REJECTED` | 审批拒绝 |
| `STAMPED` | 已完成盖章 |
| `CANCELLED` | 已取消 |
| `EXPIRED` | 已过期 |

### 2.3 盖章任务状态

| 状态 | 含义 |
|---|---|
| `CREATED` | 任务已创建 |
| `CAPTURING` | 正在拍摄纸质文件 |
| `QR_SCANNING` | 正在扫描二维码 |
| `OCR_RUNNING` | 正在运行 OCR |
| `VERIFYING` | 正在进行规则核验 |
| `PASS` | 自动验证通过 |
| `REVIEW` | 进入人工复审 |
| `REJECT` | 自动拒绝 |
| `STAMPING` | 正在机械臂盖章 |
| `STAMPED` | 已成功盖章 |
| `STAMP_FAILED` | 盖章失败 |
| `ARCHIVED` | 已归档 |

---

## 3. 系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│                       前端 React SPA                          │
│  登录 / 请假申请 / 操作台 / 人工复审 / 审计日志 / 模板 / 标定     │
│  React 19 + Vite + TypeScript + TailwindCSS + Zustand          │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTP API / MJPEG Stream
┌─────────────────────────────▼────────────────────────────────┐
│                         FastAPI 后端                          │
│  认证 · 请假申请 · 盖章任务 · OCR · 验证 · 复审 · 日志 · 标定       │
└───────┬──────────────┬─────────────┬─────────────┬────────────┘
        │              │             │             │
        ▼              ▼             ▼             ▼
   api/leave       vision/        validator/     hardware/
   请假申请 API     摄像头/OCR      请假条验证器    机械臂控制
   stamp API        二维码识别      风险评分        标定与盖章
        │              │             │             │
        └──────────────┴─────────────┴─────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                           MySQL                               │
│ users / personnel / leave_applications / stamp_tasks          │
│ verification_results / doc_templates / template_fields        │
│ audit_log / review_queue                                      │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + Vite + TypeScript + TailwindCSS v4 |
| 状态管理 | Zustand |
| 路由 | React Router |
| 图表 | Recharts |
| 后端 | Python 3.11+ + FastAPI |
| 数据库 | MySQL 8.0 + SQLAlchemy + Alembic |
| OCR | PaddleOCR / PaddlePaddle |
| 图像处理 | OpenCV / Pillow / scikit-image |
| 二维码 | pyzbar |
| 机械臂 | WeArm 串口 / Hiwonder ArmPi WiFi |
| Monorepo | Turborepo + pnpm workspaces |

---

## 4. 完整业务流程

```text
① 学生登录系统，在线提交请假申请
        │
② 系统生成 application_id，例如 LEAVE-20260511-0001
        │
③ 管理员或复审员审批申请
        │
④ 审批通过后，申请状态变为 APPROVED
        │
⑤ 系统生成带 HMAC 签名的二维码 payload
        │
⑥ 学生打印或携带带二维码的纸质请假条
        │
⑦ 操作员登录线下盖章机器人系统
        │
⑧ 将纸质请假条放入 A4 对齐槽
        │
⑨ 点击“扫描请假条并核验盖章”
        │
⑩ 摄像头拍摄 before image
        │
⑪ 系统扫描二维码并校验签名
        │
⑫ 根据 application_id 查询 LeaveApplication
        │
⑬ 检查申请是否存在、是否 APPROVED、是否未盖章
        │
⑭ PaddleOCR 识别纸质请假条全文
        │
⑮ 根据 leave 模板抽取姓名、学号、请假类型、日期、原因等字段
        │
⑯ 将 OCR 字段与线上申请记录比对
        │
⑰ 生成风险评分和决策：PASS / REVIEW / REJECT
        │
├── PASS   → 盖章前再次拍照确认纸张未移动 → 机械臂盖章 → after image → 审计日志
├── REVIEW → 进入人工复审队列 → 复审员决定是否盖章
└── REJECT → 拒绝盖章 → 显示具体原因 → 审计日志
```

---

## 5. 核验逻辑与决策机制

系统采用多层验证，不依赖单一 OCR 结果。

### 5.1 验证项

| 验证项 | 规则 | 失败处理 |
|---|---|---|
| 二维码签名验证 | 使用 HMAC-SHA256 校验二维码 payload 是否被篡改 | 失败则 REJECT |
| 申请记录验证 | application_id 必须存在于 `leave_applications` | 不存在则 REJECT |
| 申请状态验证 | 状态必须是 `APPROVED` | 未审批、拒绝、已盖章均 REJECT |
| 重复盖章验证 | `stamped_at` 必须为空 | 已盖章则 REJECT |
| 学号一致性验证 | OCR 学号必须与申请记录完全一致 | 不一致则 REJECT |
| 姓名一致性验证 | 允许空格、大小写等轻微差异 | 轻微不一致 REVIEW，明显不一致 REJECT |
| 请假类型验证 | OCR 请假类型应与申请记录一致 | 缺失 REVIEW，明显不一致 REJECT |
| 日期一致性验证 | 开始日期和结束日期必须一致，结束日期不能早于开始日期 | 缺失 REVIEW，不一致 REJECT |
| 原因字段验证 | 原因不应为空 | 为空则 REVIEW |
| OCR 置信度验证 | ≥0.85 PASS，0.65-0.85 REVIEW，<0.65 REJECT | 按阈值处理 |
| 模板匹配验证 | 文档应匹配 leave 模板 | 不匹配 REJECT，置信度低 REVIEW |
| 纸张位置验证 | 盖章前再次拍照，判断纸张是否移动 | 移动明显则 REVIEW |

### 5.2 决策结果

| 决策 | 含义 | 动作 |
|---|---|---|
| `PASS` | 低风险，所有关键验证通过 | 自动盖章 |
| `REVIEW` | 中风险，部分字段不确定 | 进入人工复审 |
| `REJECT` | 高风险或硬规则失败 | 拒绝盖章 |

### 5.3 风险分计算

建议规则：

| 类型 | 分数 |
|---|---|
| 严重失败项 | +70 |
| 一般失败项 | +40 |
| 警告项 | +10 到 +25 |
| 最高分 | 100 |

最终判断：

```text
存在 hard fail      → REJECT
risk_score >= 70   → REJECT
risk_score >= 40   → REVIEW
risk_score < 40    → PASS
```

### 5.4 验证结果示例

```json
{
  "decision": "PASS",
  "risk_score": 8,
  "checks": [
    {
      "name": "qr_signature_check",
      "result": "pass",
      "score": 0,
      "reason": "二维码签名验证通过"
    },
    {
      "name": "student_id_match_check",
      "result": "pass",
      "score": 0,
      "reason": "学号与申请记录一致"
    },
    {
      "name": "ocr_confidence_check",
      "result": "pass",
      "score": 8,
      "reason": "OCR 置信度满足自动通过阈值"
    }
  ],
  "errors": [],
  "warnings": []
}
```

---

## 6. 功能清单

| 功能 | 优先级 | 实现方式 | 状态 |
|---|---:|---|---|
| 用户登录/注册 | P0 | FastAPI auth + React 页面 | 已有 |
| 请假申请创建 | P0 | `/api/leave-applications` | 新增 |
| 请假申请审批/拒绝 | P0 | admin/reviewer 权限 | 新增 |
| 二维码 payload 生成 | P0 | HMAC-SHA256 签名 | 新增 |
| 二维码扫描 | P0 | pyzbar + OpenCV | 已有，需接入 leave 流程 |
| OCR 识别 | P0 | PaddleOCR | 已有，需接入 leave_extractor |
| 请假条字段抽取 | P0 | 模板正则 + 默认正则 | 新增 |
| 请假条规则验证 | P0 | `validator/leave_validator.py` | 新增 |
| 风险评分 | P0 | PASS / REVIEW / REJECT | 新增 |
| 自动盖章 | P0 | 现有 hardware 模块 | 已有，需接入新流程 |
| 人工复审 | P0 | review_queue + ReviewPage | 已有，需增强 |
| 审计日志 | P0 | audit_log + before/after 图片 | 已有，需增强 |
| 重复盖章检测 | P0 | `stamped_at` 和 task 状态 | 新增 |
| 纸张移动检测 | P1 | comparator / SSIM | 可选增强 |
| 盖章后质量检测 | P1 | after image + 红色区域检测 | 可选增强 |
| DMS 集成 | P2 | REST API | 可选 |

---

## 7. 数据库设计

### 7.1 `leave_applications` 请假申请表

```sql
CREATE TABLE leave_applications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  application_id VARCHAR(64) UNIQUE NOT NULL,
  student_id VARCHAR(20) NOT NULL,
  student_name VARCHAR(50) NOT NULL,
  dept VARCHAR(100),
  leave_type VARCHAR(50) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  reason TEXT NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
  qr_content TEXT,
  approved_by VARCHAR(50),
  approved_at VARCHAR(30),
  stamped_at VARCHAR(30),
  created_at VARCHAR(30),
  updated_at VARCHAR(30)
);
```

### 7.2 `stamp_tasks` 盖章任务表

```sql
CREATE TABLE stamp_tasks (
  id INT PRIMARY KEY AUTO_INCREMENT,
  task_id VARCHAR(64) UNIQUE NOT NULL,
  application_id VARCHAR(64),
  operator_id VARCHAR(50),
  doc_type VARCHAR(50) DEFAULT 'leave',
  status VARCHAR(30),
  decision VARCHAR(30),
  risk_score INT DEFAULT 0,
  before_img VARCHAR(500),
  after_img VARCHAR(500),
  qr_content TEXT,
  extracted_fields TEXT,
  verification_result TEXT,
  error_message TEXT,
  created_at VARCHAR(30),
  updated_at VARCHAR(30)
);
```

### 7.3 `verification_results` 验证结果表

```sql
CREATE TABLE verification_results (
  id INT PRIMARY KEY AUTO_INCREMENT,
  task_id VARCHAR(64) NOT NULL,
  check_name VARCHAR(100) NOT NULL,
  result VARCHAR(30) NOT NULL,
  score INT DEFAULT 0,
  reason TEXT,
  created_at VARCHAR(30)
);
```

### 7.4 扩展 `audit_log`

建议新增字段：

```sql
ALTER TABLE audit_log ADD COLUMN application_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN task_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN decision VARCHAR(30);
ALTER TABLE audit_log ADD COLUMN risk_score INT DEFAULT 0;
ALTER TABLE audit_log ADD COLUMN verification_result TEXT;
```

### 7.5 扩展 `review_queue`

建议新增字段：

```sql
ALTER TABLE review_queue ADD COLUMN application_id VARCHAR(64);
ALTER TABLE review_queue ADD COLUMN task_id VARCHAR(64);
ALTER TABLE review_queue ADD COLUMN risk_score INT DEFAULT 0;
ALTER TABLE review_queue ADD COLUMN verification_result TEXT;
```

---

## 8. 后端 API 设计

### 8.1 请假申请 API

统一前缀：

```text
/api/leave-applications
```

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/leave-applications` | 创建请假申请 |
| GET | `/api/leave-applications` | 获取申请列表，支持状态筛选 |
| GET | `/api/leave-applications/{application_id}` | 获取申请详情 |
| POST | `/api/leave-applications/{application_id}/approve` | 审批通过 |
| POST | `/api/leave-applications/{application_id}/reject` | 审批拒绝 |
| GET | `/api/leave-applications/{application_id}/qr` | 获取二维码 payload 或二维码图片 |

#### 创建请假申请请求示例

```json
{
  "student_id": "20230001",
  "student_name": "张三",
  "dept": "智能工程学院",
  "leave_type": "病假",
  "start_date": "2026-05-11",
  "end_date": "2026-05-12",
  "reason": "身体不适，需要休息"
}
```

### 8.2 盖章任务 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/stamp/leave` | 扫描请假条并核验盖章 |
| GET | `/api/stamp-tasks/{task_id}` | 获取盖章任务详情 |
| POST | `/api/stamp-tasks/{task_id}/retry` | 可选：重试失败任务 |

`POST /api/stamp/leave` 流程：

```text
创建 StampTask
→ 拍 before image
→ 扫二维码
→ 验证二维码签名
→ 查询 LeaveApplication
→ OCR
→ 抽取请假条字段
→ 规则验证
→ 保存 VerificationResult
→ PASS/REVIEW/REJECT
→ 盖章或复审或拒绝
→ 写入 audit_log
```

### 8.3 人工复审 API

沿用现有 review 模块，增强字段展示。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/review/pending` | 待复审任务列表 |
| POST | `/api/review/{id}/resolve` | 处理复审任务 |

复审通过时：

```text
确认申请仍为 APPROVED
确认 stamped_at 为空
调用盖章逻辑
更新 review_queue
更新 stamp_tasks
更新 leave_applications
写入 audit_log
```

复审拒绝时：

```text
更新 review_queue
更新 stamp_tasks
不调用机械臂
写入 audit_log
```

---

## 9. 前端页面设计

### 9.1 新增路由

| 路径 | 页面 | 权限 |
|---|---|---|
| `/applications` | 请假申请列表 | 认证用户 |
| `/applications/new` | 新建请假申请 | 认证用户 |
| `/applications/:applicationId` | 请假申请详情 | 认证用户 |

### 9.2 请假申请列表页

文件：

```text
apps/web/src/pages/LeaveApplicationsPage.tsx
```

功能：

- 显示申请列表。
- 按状态筛选。
- 显示 application_id、姓名、学号、院系、请假类型、开始日期、结束日期、状态。
- admin/reviewer 可审批或拒绝。
- 点击进入详情页。

### 9.3 新建请假申请页

文件：

```text
apps/web/src/pages/NewLeaveApplicationPage.tsx
```

字段：

- 学号 `student_id`
- 姓名 `student_name`
- 院系 `dept`
- 请假类型 `leave_type`
- 开始日期 `start_date`
- 结束日期 `end_date`
- 请假原因 `reason`

提交成功后跳转申请详情页。

### 9.4 请假申请详情页

文件：

```text
apps/web/src/pages/LeaveApplicationDetailPage.tsx
```

展示：

- 申请详情。
- 当前状态。
- 二维码 payload 或二维码图片。
- 审批信息。
- 盖章时间。

### 9.5 操作台页面

主按钮改为：

```text
扫描请假条并核验盖章
```

调用：

```text
POST /api/stamp/leave
```

展示：

- application_id
- task_id
- student_id
- student_name
- leave_type
- start_date
- end_date
- decision
- risk_score
- checks
- errors
- warnings
- before_img
- after_img
- 最终状态

### 9.6 复审页面

增强现有 ReviewPage，显示：

- task_id
- application_id
- risk_score
- extracted_fields
- verification_result
- warnings
- before image
- approve / reject 操作

### 9.7 日志页面

增强现有 LogsPage，新增显示：

- application_id
- task_id
- decision
- risk_score
- verification_result

旧日志没有这些字段时，页面不能崩溃。

---

## 10. 请假条模板与 OCR 字段抽取

### 10.1 leave 模板配置

确保 `doc_templates` 中存在：

```json
{
  "code": "leave",
  "name": "请假条",
  "requires_stamp": 1,
  "stamp_position": "420,650",
  "classification_keywords": [
    "请假条",
    "请假申请",
    "Leave Request",
    "Leave Application"
  ],
  "stamp_keywords": [
    "审批意见",
    "学院盖章",
    "Stamp",
    "Approved"
  ]
}
```

### 10.2 template_fields 字段

确保 leave 模板包含以下字段：

| 字段名 | 标签 | 必填 | 示例 |
|---|---|---|---|
| application_id | 申请编号 | 是 | LEAVE-20260511-0001 |
| student_name | 姓名 | 是 | 张三 |
| student_id | 学号 | 是 | 20230001 |
| dept | 院系 | 可选 | 智能工程学院 |
| leave_type | 请假类型 | 是 | 病假 |
| start_date | 开始日期 | 是 | 2026-05-11 |
| end_date | 结束日期 | 是 | 2026-05-12 |
| reason | 请假原因 | 是 | 身体不适 |

### 10.3 字段抽取模块

新增文件：

```text
apps/backend/vision/leave_extractor.py
```

核心函数：

```python
extract_leave_fields(ocr_text: str, template_fields: list | None = None) -> dict
```

抽取字段：

```text
application_id
student_name
student_id
dept
leave_type
start_date
end_date
reason
```

抽取策略：

```text
优先使用 template_fields.ocr_pattern
失败后使用默认正则兜底
日期统一转成 YYYY-MM-DD
字段缺失时返回 None 或空字符串，不抛致命异常
```

---

## 11. 机械臂盖章与安全控制

### 11.1 盖章坐标

优先使用模板配置：

```text
stamp_position = "420,650"
```

如果存在 stamp_keywords，则可结合关键词定位。

推荐顺序：

```text
固定模板坐标 → 关键词附近定位 → 默认安全坐标 → 人工复审
```

### 11.2 盖章前纸张位置确认

PASS 后不要立即盖章，需再次拍照：

```text
验证通过
→ 盖章前再次拍照
→ 检查纸张位置是否明显偏移
→ 未偏移才执行机械臂盖章
→ 偏移则进入 REVIEW
```

### 11.3 盖章后拍照

盖章后拍摄 after image，用于：

- 审计留痕。
- 判断机械臂是否执行完成。
- 后续可扩展为印章成功检测。

### 11.4 仿真模式

开发和测试阶段优先使用：

```python
SIMULATION_MODE = True
```

仿真模式下：

- 不连接真实机械臂。
- PASS 时返回模拟盖章成功。
- 仍写入 StampTask、VerificationResult、audit_log。

---

## 12. Superpower 分阶段开发方案

开发要求：

1. 不要一次性大规模重构。
2. 每次只完成一个小的、可验证的功能点。
3. 每完成一个功能点，必须立即运行快速测试。
4. 测试通过后，再继续下一个功能点。
5. 如果测试失败，先修复当前功能，不要继续往后做。
6. 尽量复用现有代码，不要推翻重写。
7. 每一步修改后输出：
   - 修改了哪些文件。
   - 新增了哪些接口或函数。
   - 如何快速测试。
   - 测试结果是否通过。
   - 下一步计划。

### 阶段 1：数据库模型与迁移

目标：新增请假申请、盖章任务、验证结果相关数据结构。

需要完成：

- 新增 `LeaveApplication`。
- 新增 `StampTask`。
- 新增 `VerificationResult`。
- 创建 Alembic migration 或使用项目现有初始化逻辑。
- 确保不影响已有 `users`、`personnel`、`doc_templates`、`template_fields`、`audit_log`、`review_queue`。

快速测试：

```text
1. 运行数据库迁移。
2. 检查 MySQL 中是否存在：
   - leave_applications
   - stamp_tasks
   - verification_results
3. 启动后端。
4. 打开 http://127.0.0.1:5001/docs。
5. 确认服务无报错。
```

通过标准：

- 后端可以正常启动。
- 新表成功创建。
- 原有登录接口不报错。
- 原有模板管理接口不报错。

### 阶段 2：二维码签名工具

目标：实现二维码内容生成和防篡改验证。

新增文件：

```text
apps/backend/utils/qr_sign.py
```

快速测试：

```python
from utils.qr_sign import create_leave_qr_payload, verify_qr_payload

payload = create_leave_qr_payload("LEAVE-20260511-0001", "20230001")
assert verify_qr_payload(payload) is True

payload["student_id"] = "99999999"
assert verify_qr_payload(payload) is False

print("QR sign test passed")
```

通过标准：

- 正常 payload 验证通过。
- 篡改 student_id 后验证失败。
- 后端启动不受影响。

### 阶段 3：请假申请 API

目标：实现创建、查询、审批、拒绝和二维码查看。

快速测试：

```bash
curl -X POST http://127.0.0.1:5001/api/leave-applications \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "20230001",
    "student_name": "张三",
    "dept": "智能工程学院",
    "leave_type": "病假",
    "start_date": "2026-05-11",
    "end_date": "2026-05-12",
    "reason": "身体不适，需要休息"
  }'
```

```bash
curl http://127.0.0.1:5001/api/leave-applications
curl -X POST http://127.0.0.1:5001/api/leave-applications/LEAVE-20260511-0001/approve
curl http://127.0.0.1:5001/api/leave-applications/LEAVE-20260511-0001/qr
```

通过标准：

- 可以创建请假申请。
- application_id 自动生成。
- qr_content 自动生成。
- 可以查询申请。
- 可以审批通过。
- 审批后 status = APPROVED。

### 阶段 4：请假条 OCR 字段抽取

快速测试：

```python
from vision.leave_extractor import extract_leave_fields

text = '''
请假条
申请编号：LEAVE-20260511-0001
姓名：张三
学号：20230001
院系：智能工程学院
请假类型：病假
开始日期：2026-05-11
结束日期：2026-05-12
请假原因：身体不适，需要休息
'''

fields = extract_leave_fields(text)
assert fields["application_id"] == "LEAVE-20260511-0001"
assert fields["student_name"] == "张三"
assert fields["student_id"] == "20230001"
assert fields["leave_type"] == "病假"
assert fields["start_date"] == "2026-05-11"
assert fields["end_date"] == "2026-05-12"
assert "身体不适" in fields["reason"]

print("Leave extractor test passed")
```

通过标准：

- 中文请假条字段能正确抽取。
- 英文请假条字段能正确抽取。
- 日期格式统一为 YYYY-MM-DD。
- 缺字段时不崩溃。

### 阶段 5：请假条验证器

目标：实现 PASS / REVIEW / REJECT 决策。

测试场景：

| 场景 | 预期 |
|---|---|
| 正常申请 + 字段一致 + OCR 置信度高 | PASS |
| 未审批申请 | REJECT |
| 学号不一致 | REJECT |
| OCR 置信度中等 | REVIEW |
| 已盖章申请再次扫描 | REJECT |
| 二维码被篡改 | REJECT |

通过标准：

- 每个结果都有 checks 和 reason。
- 不出现未捕获异常。
- hard fail 一定不会自动盖章。

### 阶段 6：请假条盖章接口

接口：

```text
POST /api/stamp/leave
```

快速测试：

```bash
curl -X POST http://127.0.0.1:5001/api/stamp/leave
```

通过标准：

- 返回 success。
- 返回 task_id。
- 返回 decision。
- 返回 checks。
- SIMULATION_MODE 下不连接机械臂也不崩溃。
- `stamp_tasks` 有记录。
- `verification_results` 有记录。
- `audit_log` 有记录。

### 阶段 7：人工复审流程

快速测试：

```bash
curl http://127.0.0.1:5001/api/review/pending
```

通过标准：

- REVIEW 任务可以被处理。
- 通过时能盖章或仿真盖章。
- 拒绝时不会盖章。
- 数据状态一致。

### 阶段 8：前端请假申请页面

快速测试：

```bash
pnpm dev
```

打开：

```text
http://localhost:5173/applications
```

通过标准：

- 页面不白屏。
- 表单能提交。
- 列表能刷新。
- 详情能打开。
- 审批按钮可用。
- 后端数据状态正确变化。

### 阶段 9：前端操作台接入

通过标准：

- PASS 显示“验证通过，已自动盖章”。
- REVIEW 显示“验证不确定，已进入人工复审”。
- REJECT 显示“验证失败，拒绝盖章”。
- checks 能逐项展示。
- 错误信息清晰。
- 页面不崩溃。

### 阶段 10：复审页面和日志页面增强

通过标准：

- 复审页面能处理任务。
- 日志页面能显示新字段。
- 旧日志不会导致页面报错。
- 图片路径能正常显示或有降级提示。

---

## 13. 最终验收标准

### 验收 1：正常通过流程

步骤：

1. admin 登录。
2. 创建请假申请：
   - student_id = 20230001
   - student_name = 张三
   - leave_type = 病假
   - start_date = 2026-05-11
   - end_date = 2026-05-12
   - reason = 身体不适
3. 管理员审批通过。
4. 详情页显示二维码 payload。
5. 将二维码放到请假条中。
6. 操作台点击“扫描请假条并核验盖章”。
7. 系统完成二维码验证、OCR、字段比对、风险评分。
8. 返回 decision = PASS。
9. 机械臂执行盖章，或仿真模式显示已盖章。
10. LeaveApplication 状态变为 STAMPED。
11. audit_log 有完整记录。
12. before_img 和 after_img 有路径。

通过标准：

- 整个流程无报错。
- 数据库状态正确。
- 页面展示清晰。
- 审计日志完整。

### 验收 2：未审批申请拒绝流程

步骤：

1. 创建请假申请，但不审批。
2. 扫描请假条。
3. 系统返回 REJECT。
4. 原因包含“申请尚未审批”。
5. 不调用机械臂。
6. audit_log 有拒绝记录。

通过标准：

> 未审批申请绝不会被盖章。

### 验收 3：学号不一致拒绝流程

步骤：

1. 创建并审批申请。
2. 纸质请假条中的学号改成另一个。
3. 扫描。
4. 系统返回 REJECT。
5. 原因包含“学号不一致”。
6. 不调用机械臂。

通过标准：

> 学号不一致绝不会被盖章。

### 验收 4：OCR 不清楚复审流程

步骤：

1. 准备 OCR 置信度较低或缺字段的请假条。
2. 扫描。
3. 系统返回 REVIEW。
4. review_queue 出现任务。
5. 复审页面能看到任务。
6. 复审员可以通过或拒绝。

通过标准：

> 不确定情况不会自动盖章，必须进入人工复审。

### 验收 5：重复盖章拒绝流程

步骤：

1. 同一申请第一次盖章成功。
2. 再次扫描同一二维码。
3. 系统返回 REJECT。
4. 原因包含“该申请已盖章”。
5. 不调用机械臂。

通过标准：

> 同一申请不能重复盖章。

### 验收 6：二维码篡改拒绝流程

步骤：

1. 修改二维码 payload 中的 student_id 或 application_id。
2. 保持 sig 不变。
3. 扫描。
4. 系统返回 REJECT。
5. 原因包含“二维码签名无效”或“二维码验证失败”。

通过标准：

> 篡改二维码无法通过验证。

### 验收 7：系统兼容性验收

确认旧功能仍可用：

- 登录
- 注册
- 用户管理
- 模板管理
- 摄像头预览
- 机械臂标定
- 人工复审
- 审计日志
- 原有通用盖章接口

通过标准：

- 旧页面不白屏。
- 旧接口不报 500。
- 新增功能不破坏原系统。

---

## 14. 软件环境与安装

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm
- MySQL 8.0
- 内存 4GB+，PaddleOCR 模型加载需要约 1.5GB

### 安装依赖

```bash
# 克隆项目后进入根目录
cd MEC202

# 安装 pnpm
npm install -g pnpm

# 安装前端与 monorepo 依赖
pnpm install

# 安装后端依赖
cd apps/backend
pip install -r requirements.txt
# 或使用 uv
uv sync
```

### 数据库初始化

```bash
cd apps/backend
alembic upgrade head
```

如果项目未使用 Alembic，则使用现有初始化脚本创建数据库表。

---

## 15. 快速启动

### Turborepo 启动

```bash
pnpm dev
```

### 手动启动

```bash
# 终端 1：启动后端
cd apps/backend
python -m api.main

# 终端 2：启动前端
cd apps/web
pnpm dev
```

### 访问地址

| 模式 | 地址 |
|---|---|
| 前端开发 | http://localhost:5173 |
| 后端 API | http://127.0.0.1:5001 |
| Swagger | http://127.0.0.1:5001/docs |
| ReDoc | http://127.0.0.1:5001/redoc |

### 演示账号

| 账号 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| operator1 | op123 | 操作员 |
| reviewer1 | reviewer123 | 复审员 |

---

## 16. 正式运行：接硬件

1. 连接 USB 摄像头。
2. 连接 WeArm 机械臂或 Hiwonder ArmPi。
3. 确认 MySQL 正常运行。
4. 设置 `SIMULATION_MODE = False`。
5. 启动服务：

```bash
pnpm dev
```

6. 打开浏览器登录系统。
7. 进入机械臂标定页面，完成四角标定。
8. 进入操作台，执行“扫描请假条并核验盖章”。

---

## 17. 项目文件结构

```text
MEC202/
├── turbo.json
├── pnpm-workspace.yaml
├── package.json
│
├── apps/
│   ├── backend/
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── auth.py
│   │   │   ├── leave_applications.py   # 新增：请假申请 API
│   │   │   ├── stamp.py                # 修改：接入 /api/stamp/leave
│   │   │   ├── review.py               # 修改：接入 leave task
│   │   │   ├── cameras.py
│   │   │   ├── logs.py
│   │   │   ├── templates.py
│   │   │   ├── calibration.py
│   │   │   └── users.py
│   │   │
│   │   ├── database/
│   │   │   ├── models.py               # 新增 LeaveApplication / StampTask / VerificationResult
│   │   │   └── connection.py
│   │   │
│   │   ├── vision/
│   │   │   ├── ocr.py
│   │   │   ├── qr_scanner.py
│   │   │   ├── classifier.py
│   │   │   ├── comparator.py
│   │   │   └── leave_extractor.py      # 新增：请假条字段抽取
│   │   │
│   │   ├── validator/
│   │   │   └── leave_validator.py      # 新增：请假条验证器
│   │   │
│   │   ├── hardware/
│   │   └── utils/
│   │       └── qr_sign.py              # 新增：二维码签名工具
│   │
│   └── web/
│       └── src/
│           ├── App.tsx                 # 修改：新增路由
│           ├── pages/
│           │   ├── LeaveApplicationsPage.tsx
│           │   ├── NewLeaveApplicationPage.tsx
│           │   ├── LeaveApplicationDetailPage.tsx
│           │   ├── ReviewPage.tsx
│           │   └── LogsPage.tsx
│           ├── lib/
│           │   └── api.ts
│           └── types/
│               └── index.ts
```

---

## 18. 团队分工

| 成员 | 负责模块 | 核心文件 | 交付标准 |
|---|---|---|---|
| 甲：硬件 | 机械臂、标定、盖章路径 | `apps/backend/hardware/` | 机械臂能稳定盖章，仿真/真实模式可切换 |
| 乙：视觉 | OCR、二维码、字段抽取 | `vision/ocr.py`, `vision/qr_scanner.py`, `vision/leave_extractor.py` | 请假条字段抽取准确，二维码识别稳定 |
| 丙：验证逻辑 | 请假条验证器、风险评分 | `validator/leave_validator.py` | PASS/REVIEW/REJECT 逻辑清晰可靠 |
| 丁：前端 | 请假申请、操作台、复审、日志 | `apps/web/src/pages/` | 页面完整，结果展示清晰 |
| 戊：集成 | API、数据库、端到端流程 | `api/leave_applications.py`, `api/stamp.py`, `database/models.py` | 全流程端到端跑通 |

---

## 19. 开发时间线

```text
Week 1：数据库模型、二维码签名、请假申请 API
Week 2：OCR 字段抽取、请假条验证器、模板字段配置
Week 3：/api/stamp/leave 全流程打通，仿真模式测试
Week 4：前端请假申请页面、操作台接入、复审页面增强
Week 5：硬件联调、机械臂盖章、纸张位置确认
Week 6：异常场景测试、验收 Demo、报告和视频录制
```

---

## 20. 硬件组装指南

### 框架搭建

1. 使用 KT 板搭建 A4 对齐槽。
2. 摄像头固定在顶部中央，正对文件区域。
3. 机械臂固定在侧边，末端安装印章。
4. 底板标出 A4 放置区域。
5. 确保纸张放入后位置稳定，不易偏移。

### 标定

1. 打开 `/calibration` 页面。
2. 测试机械臂连接。
3. 调整舵机到四角位置。
4. 保存 TL/TR/BL/BR 四角标定点。
5. 测试盖章点是否准确。

---

## 21. 配置说明

`apps/backend/config.py` 关键配置：

```python
# 机械臂类型
ARM_TYPE = 'wearm'  # 'wearm' 或 'hiwonder'

# 仿真模式
SIMULATION_MODE = True  # 开发阶段建议 True，接硬件后改 False

# 数据库配置
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'stamp_robot'
DB_PASSWORD = 'stamp_robot_pwd'
DB_NAME = 'stamp_robot'

# Web 安全
SECRET_KEY = 'stamp_robot_mec202_secret'

# 摄像头与纸张检测
PAPER_DETECTION_ENABLED = False
```

---

## 22. 常见问题

### Q1：为什么不能只靠模板判断？

因为模板只能判断“格式像不像”，不能证明“这份文件是否真的经过线上审批”。本系统通过 application_id 和二维码签名绑定线上申请记录，再用 OCR 与数据库比对，从而判断纸质请假条是否真实有效。

### Q2：二维码被学生修改怎么办？

二维码 payload 使用 HMAC-SHA256 签名。只要修改 application_id 或 student_id，签名验证就会失败，系统会拒绝盖章。

### Q3：OCR 识别不清楚怎么办？

OCR 置信度低或字段缺失时，不自动盖章，而是进入人工复审。

### Q4：同一个申请能不能盖两次？

不能。第一次盖章成功后，`LeaveApplication.status` 变为 `STAMPED`，`stamped_at` 不为空。再次扫描同一二维码会被拒绝。

### Q5：没有机械臂时能不能开发？

可以。设置：

```python
SIMULATION_MODE = True
```

系统会模拟盖章成功，但仍然写入任务、验证结果和审计日志。

---

## 23. 采购清单

| # | 淘宝搜索词 | 规格要求 | 预估价 |
|---|---|---|---:|
| 1 | Arduino Uno R3 开发板 官方兼容 | 含 USB 线 | ~40¥ |
| 2 | MG996R 舵机 金属齿轮 | 1 个 | ~25¥ |
| 3 | MG90S 微型舵机 | 1 个 | ~15¥ |
| 4 | 1080P USB 摄像头 免驱 广角 | 即插即用 | ~60¥ |
| 5 | 光敏印章 自动回墨 定制刻字 | 刻“已审核”或“Approved” | ~25¥ |
| 6 | KT 板 A3 白色 5mm | 3-5 张 | ~15¥ |
| 7 | 热熔胶枪套装 | 含胶棒 | ~20¥ |
| 8 | 杜邦线 公对母 20cm 40 根 | 1 包 | ~8¥ |
| | | **总计** | **~208¥** |

---

## 24. 给 Claude Code 的改造任务说明

请使用以下要求进行代码改造：

```text
你正在修改 MEC202 文档盖章机器人项目。

请先阅读整个项目结构，不要重写项目，不要推翻现有代码。请在现有 FastAPI、React、MySQL、OCR、二维码、机械臂、审计日志、人工复审模块基础上增量修改。

改造目标：
把当前通用文档识别盖章系统，改造成“线上请假申请 + 线下请假条核验 + 自动盖章”的完整闭环系统。

核心业务：
学生先在线提交请假申请，系统创建申请记录并生成二维码。管理员审批通过后，学生携带带二维码的纸质请假条到线下机器人处。系统扫描二维码，根据 application_id 查询申请记录，通过 OCR 识别纸质内容，并与线上申请记录比对。只有申请真实存在、已审批、未重复盖章、纸质内容一致时，才允许自动盖章。

必须新增：
1. LeaveApplication 模型和 leave_applications 表。
2. StampTask 模型和 stamp_tasks 表。
3. VerificationResult 模型和 verification_results 表。
4. utils/qr_sign.py，实现 HMAC-SHA256 二维码签名和验证。
5. api/leave_applications.py，实现请假申请创建、查询、审批、拒绝、二维码查看。
6. vision/leave_extractor.py，实现请假条 OCR 字段抽取。
7. validator/leave_validator.py，实现 PASS / REVIEW / REJECT 验证器。
8. POST /api/stamp/leave，实现请假条扫描、核验、盖章流程。
9. 前端新增 /applications、/applications/new、/applications/:applicationId 页面。
10. 修改操作台按钮为“扫描请假条并核验盖章”。
11. 增强 review 和 logs 页面，显示 application_id、task_id、risk_score、verification_result。

必须遵守 Superpower 模式：
1. 不要一次性大规模重构。
2. 每次只完成一个小的可验证功能点。
3. 每完成一个阶段就运行快速测试。
4. 测试失败时先修复，不要继续往后做。
5. 每阶段输出修改文件、测试方式、测试结果和下一步计划。

最终验收必须通过：
1. 正常申请审批后可以自动盖章。
2. 未审批申请必须 REJECT。
3. 学号不一致必须 REJECT。
4. OCR 不清楚必须 REVIEW。
5. 重复盖章必须 REJECT。
6. 二维码篡改必须 REJECT。
7. 原有登录、模板、摄像头、标定、复审、日志功能不能被破坏。
```

---

*项目使用 Turborepo Monorepo · Python FastAPI · React 19 · PaddleOCR · MySQL · OpenCV · pyzbar · 机械臂自动盖章*
