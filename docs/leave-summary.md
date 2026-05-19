# 请假条相关功能总结

> 最后更新：2026/05/19

---

## 一、概述

项目中的请假条功能是一套**线上请假申请 + 线下核验盖章**的完整闭环系统。学生在线提交请假申请，管理员审批后生成带 HMAC 签名二维码的请假条，操作员在盖章机器人处扫描二维码、OCR 识别纸质内容并与线上记录比对，只有验证通过才允许自动盖章。

---

## 二、角色权限

| 角色 | 权限 |
|---|---|
| **admin（管理员）** | 可审批/拒绝任何请假申请，查看所有页面 |
| **reviewer（审批员）** | 可审批/拒绝任何请假申请，查看审计日志和人工复审 |
| **operator（操作员）** | 只能查看自己创建的申请和申请状态，**不能审批/拒绝** |

---

## 三、业务流程

```
创建申请 → 审批 → 下载PDF打印 → 摄像头盖章
```

1. **创建申请**：任意登录用户在 `/applications/new` 提交请假申请，状态变为 `SUBMITTED`
2. **审批**：admin/reviewer 审批通过后状态变为 `APPROVED`，生成带 HMAC 签名的二维码
3. **下载打印**：审批通过后，详情页显示二维码和 PDF 下载链接
4. **盖章**：操作台切换到"请假"模式，点击盖章按钮，SSE 流式执行：拍照 → 扫描二维码 → GLM-4V 视觉识别 → 10 项核验检查 → 盖章或进入复审

---

## 四、状态流转

```
SUBMITTED ──审批通过──→ APPROVED ──盖章成功──→ STAMPED
     │                      │
     └──拒绝──→ REJECTED    └──盖章失败──→ 复审队列
```

---

## 五、关键文件清单

### 5.1 后端

| 文件 | 说明 |
|---|---|
| `apps/backend/api/leave_applications.py` | 请假申请 CRUD、审批、拒绝、PDF 下载 |
| `apps/backend/api/stamp.py` | SSE 流式盖章流程（`/stamp/leave`） |
| `apps/backend/validator/leave_validator.py` | 10 项核验检查，PASS/REVIEW/REJECT 决策 |
| `apps/backend/vision/leave_extractor.py` | OCR 字段抽取（申请编号、姓名、学号、日期等） |
| `apps/backend/utils/qr_sign.py` | HMAC-SHA256 二维码签名和验证 |
| `apps/backend/database/models.py` | `LeaveApplication`、`StampTask`、`VerificationResult` 模型 |

### 5.2 前端

| 文件 | 说明 |
|---|---|
| `apps/web/src/pages/LeaveApplicationsPage.tsx` | 请假列表页 |
| `apps/web/src/pages/NewLeaveApplicationPage.tsx` | 新建申请表单页 |
| `apps/web/src/pages/LeaveApplicationDetailPage.tsx` | 申请详情页 |
| `apps/web/src/i18n/locales/zh/applications.json` | 中文国际化 |
| `apps/web/src/i18n/locales/en/applications.json` | 英文国际化 |

### 5.3 文档

| 文件 | 说明 |
|---|---|
| `docs/leave-application-flow.md` | 业务审批流程文档 |
| `doc/README_leave_request_stamping.md` | 完整项目说明文档 |

---

## 六、数据库模型

### 6.1 `leave_applications` — 请假申请表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INT | 主键 |
| `application_id` | VARCHAR(64) | 唯一申请编号，格式 `LEAVE-YYYYMMDD-NNNN` |
| `student_id` | VARCHAR(20) | 学号 |
| `student_name` | VARCHAR(50) | 学生姓名 |
| `dept` | VARCHAR(100) | 院系 |
| `leave_type` | VARCHAR(50) | 请假类型（病假/事假等） |
| `start_date` | VARCHAR(30) | 开始日期 |
| `end_date` | VARCHAR(30) | 结束日期 |
| `reason` | TEXT | 请假原因 |
| `status` | VARCHAR(30) | SUBMITTED / APPROVED / REJECTED / STAMPED |
| `qr_content` | TEXT | 二维码 payload 字符串 |
| `approved_by` | VARCHAR(50) | 审批人 |
| `approved_at` | VARCHAR(30) | 审批时间 |
| `stamped_at` | VARCHAR(30) | 盖章时间 |
| `created_by` | VARCHAR(50) | 创建者 |
| `created_at` | VARCHAR(30) | 创建时间 |
| `updated_at` | VARCHAR(30) | 更新时间 |

### 6.2 `stamp_tasks` — 盖章任务表

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_id` | VARCHAR(64) | 唯一任务编号 |
| `application_id` | VARCHAR(64) | 关联的请假申请编号 |
| `operator_id` | VARCHAR(50) | 操作员 |
| `doc_type` | VARCHAR(50) | 固定为 `leave` |
| `status` | VARCHAR(30) | CREATED / PASS / REVIEW / REJECT / STAMPED 等 |
| `decision` | VARCHAR(30) | PASS / REVIEW / REJECT |
| `risk_score` | INT | 风险评分 |
| `before_img` | VARCHAR(500) | 盖章前图片路径 |
| `after_img` | VARCHAR(500) | 盖章后图片路径 |
| `qr_content` | TEXT | 二维码内容 |
| `extracted_fields` | TEXT | OCR 抽取的字段 JSON |
| `verification_result` | TEXT | 核验结果 JSON |
| `error_message` | TEXT | 错误信息 |

### 6.3 `verification_results` — 验证结果表

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_id` | VARCHAR(64) | 关联的任务编号 |
| `check_name` | VARCHAR(100) | 检查项名称 |
| `result` | VARCHAR(30) | pass / warn / fail |
| `score` | INT | 风险分值 |
| `reason` | TEXT | 说明 |

---

## 七、API 接口

### 7.1 请假申请 `/api/leave-applications`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/` | 创建请假申请 | 认证用户 |
| GET | `/` | 获取申请列表 | admin/reviewer 全部，operator 仅自己的 |
| GET | `/{application_id}` | 获取申请详情 | 认证用户 |
| POST | `/{application_id}/approve` | 审批通过 | admin/reviewer |
| POST | `/{application_id}/reject` | 审批拒绝 | admin/reviewer |
| GET | `/{application_id}/qr` | 获取二维码 payload | 认证用户 |
| GET | `/{application_id}/qr/image` | 获取二维码 PNG 图片 | 认证用户 |
| GET | `/{application_id}/download` | 下载请假条 PDF | 认证用户 |

### 7.2 盖章 `/api/stamp`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/stamp` | 通用盖章接口 |
| POST | `/stamp/leave` | 请假条核验盖章（SSE 流式） |

---

## 八、核验逻辑

`POST /api/stamp/leave` 执行 10 项检查：

| # | 检查项 | 规则 | 失败分值 |
|---|---|---|---:|
| 1 | 二维码签名验证 | HMAC-SHA256 校验 payload | 70 |
| 2 | 申请记录存在性 | application_id 必须存在 | 70 |
| 3 | 申请状态验证 | 状态必须为 APPROVED | 70 |
| 4 | 重复盖章检测 | stamped_at 必须为空 | 70 |
| 5 | 学号一致性 | OCR 学号 = 申请记录学号 | 70 |
| 6 | 姓名一致性 | 允许空格、大小写等轻微差异 | 40 |
| 7 | 请假类型一致性 | OCR 类型 = 申请记录类型 | 40 |
| 8 | 日期一致性 | 开始/结束日期必须一致 | 40 |
| 9 | 原因字段验证 | 原因字段不应为空 | 25 |
| 10 | OCR 置信度 | ≥0.85 PASS，0.65-0.85 REVIEW，<0.65 REJECT | 40 |

**决策规则：**

- 存在 hard fail（分值 70 的失败项）→ REJECT
- `risk_score >= 70` → REJECT
- `risk_score >= 40` → REVIEW
- `risk_score < 40` → PASS

---

## 九、二维码签名

`apps/backend/utils/qr_sign.py` 实现 HMAC-SHA256 防篡改：

```python
# 生成
payload = create_leave_qr_payload(application_id, student_id)
# payload = {"application_id": "...", "student_id": "...", "nonce": "...", "sig": "..."}
qr_content = qr_payload_to_string(payload)  # 序列化后生成二维码

# 验证
payload = qr_string_to_payload(qr_string)
verify_qr_payload(payload)  # 返回 True/False
```

---

## 十、前端页面

| 路径 | 页面 | 说明 |
|---|---|---|
| `/applications` | LeaveApplicationsPage | 请假申请列表 |
| `/applications/new` | NewLeaveApplicationPage | 新建请假申请 |
| `/applications/:id` | LeaveApplicationDetailPage | 申请详情 + 审批按钮 |

操作台 `/` 切换到"请假"模式后，点击盖章按钮调用 `POST /api/stamp/leave`，SSE 流式展示：拍照 → 扫描二维码 → GLM-4V 识别 → 核验结果 → 盖章/复审/拒绝。

---

## 十一、示例图片

示例请假条图片：`apps/backend/example_images/leave_example.jpg`

审计图片目录：`apps/backend/audit_images/`（包含大量 `leave_before.jpg`、`leave_pre_stamp.jpg`、`leave_after.jpg`）

---

## 十二、相关配置

关键配置在 `apps/backend/config.py`：

- `ARM_TYPE` — 机械臂类型（`wearm` / `hiwonder`）
- `SIMULATION_MODE` — 仿真模式，开发阶段建议 True
- `SECRET_KEY` — HMAC 签名密钥
- `VLM_API_KEY` / `VLM_BASE_URL` / `VLM_MODEL` — GLM-4V 视觉模型配置