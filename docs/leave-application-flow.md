# 请假申请业务审批流程

## 角色权限

| 角色 | 权限 |
|---|---|
| **admin（管理员）** | 可审批/拒绝任何请假申请，查看所有页面 |
| **reviewer（审批员）** | 可审批/拒绝任何请假申请，查看审计日志和人工复审 |
| **operator（操作员）** | 只能查看自己创建的申请和申请状态，**不能审批/拒绝** |

## 完整业务流程

```
创建申请 ──→ 审批 ──→ 下载PDF打印 ──→ 摄像头盖章
```

### 1. 创建请假申请
- 任意登录用户在 `/applications/new` 提交请假申请
- 状态变为 `SUBMITTED`（等待审批）
- 系统记录 `created_by`（创建者用户名）

### 2. 审批
- **仅 admin/reviewer** 可见审批/拒绝按钮（前端 + 后端双重鉴权）
- 后端 API：`POST /api/leave-applications/{id}/approve` 和 `/reject` 使用 `require_role("admin", "reviewer")` 保护
- 审批通过 → 状态变为 `APPROVED`，生成带 HMAC 签名的二维码
- 拒绝 → 状态变为 `REJECTED`

### 3. 下载 & 打印
- 审批通过后，详情页显示二维码和 PDF 下载链接
- API：`GET /api/leave-applications/{id}/download` 生成带二维码的请假条 PDF
- 用户打印 PDF 纸质版

### 4. 盖章（操作台）
- 用户将打印的纸质请假条放在摄像头下
- 在操作台 `/` 切换到"请假"模式，点击盖章按钮
- 后端 SSE 流式执行：
  1. 拍照
  2. 扫描二维码 → 解析 `application_id`
  3. GLM-4V 视觉识别提取请假条字段
  4. 10 项核验检查（签名验证、状态校验、字段匹配等）
  5. 核验通过 → 机械臂盖章 → 状态变为 `STAMPED`
  6. 核验存疑 → 推入人工复审队列
- API：`POST /api/stamp/leave`（SSE 流式）

## 状态流转

```
SUBMITTED ──审批通过──→ APPROVED ──盖章成功──→ STAMPED
     │                      │
     └──拒绝──→ REJECTED    └──盖章失败──→ 复审队列
```

## 关键文件

| 层级 | 文件 | 说明 |
|---|---|---|
| 前端列表 | `apps/web/src/pages/LeaveApplicationsPage.tsx` | 请假列表，operator 只能看自己的 |
| 前端详情 | `apps/web/src/pages/LeaveApplicationDetailPage.tsx` | 详情页，审批按钮仅 admin/reviewer 可见 |
| 前端新建 | `apps/web/src/pages/NewLeaveApplicationPage.tsx` | 新建申请表单 |
| 后端 API | `apps/backend/api/leave_applications.py` | CRUD、审批、拒绝、PDF 下载 |
| 后端盖章 | `apps/backend/api/stamp.py` | SSE 流式盖章流程 |
| 后端核验 | `apps/backend/validator/leave_validator.py` | 10 项核验检查 |
| 后端鉴权 | `apps/backend/api/deps.py` | `require_role()` 依赖注入 |
| 数据模型 | `apps/backend/database/models.py` | LeaveApplication 表结构 |
