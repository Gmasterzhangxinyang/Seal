# 语音控制模块 - Dify 工作流设计文档

> 本文档供 Dify 开发使用，说明语音模块能力、需要调用的后端 API 接口

---

## 一、功能概述

语音模块让用户通过语音控制机械臂完成打招呼、盖章、查询请假记录等操作。

### 三大功能

| 功能 | 接口 | 说明 |
|---|---|---|
| **语音对话 + 工具调用** | `POST /api/voice/chat` | 语音理解 → 调用工具 → 自然回复 |
| **语音识别（ASR）** | `POST /api/voice/asr` | 音频 → 文字（阿里云 Fun-ASR） |
| **语音合成（TTS）** | `POST /api/voice/tts` | 文字 → 音频（Fish Audio） |

---

## 二、语音对话工具（tools）

语音助手（小臂）可调用以下工具：

### 工具列表

| 工具名 | 说明 | 参数 |
|---|---|---|
| `arm_home` | 机械臂回中位（所有舵机归零） | 无 |
| `arm_move` | 移动机械臂到指定位置 | `servos`: {0-5舵机的 PWM 值 500-2500} |
| `arm_greet` | 打招呼动作（手腕抬起再放下） | 无 |
| `stamp_leave_check` | 智能盖章（拍照→扫码→识别→核验→盖章） | 无 |
| `query_leave_history` | 查询历史请假记录 | `name`: 学生姓名（可选） |
| `query_audit_logs` | 查询最近的盖章操作日志 | 无 |

### 工具返回示例

```
arm_home → "机械臂已回到中位"
arm_greet → "打招呼动作完成，手腕抬起又放下了"
stamp_leave_check → "核验通过，申请编号: LEAVE-20260519-0001"
stamp_leave_check → "核验未通过（REJECT）。原因：学号不一致"
query_leave_history → "请假记录：\n张三（计算机系）病假，2026-05-10到2026-05-11，状态：APPROVED"
query_audit_logs → "最近盖章记录：\n2026-05-19 10:30:12，operator1，leave，结果：APPROVED"
```

---

## 三、对话流程

```
用户说话 → ASR 识别文字 → 调用 /voice/chat → 返回回复文字 → TTS 合成语音
```

### 典型对话场景

**场景1：用户说"小臂，回中位"**
```
调用 arm_home → "机械臂已回到中位" → 告知用户
```

**场景2：用户说"小臂，帮我盖个章"**
```
调用 stamp_leave_check → 返回核验结果 → 告知用户盖章是否成功
```

**场景3：用户说"小臂，帮我查一下张三的请假记录"**
```
调用 query_leave_history(name="张三") → 返回请假记录列表 → 告知用户
```

**场景4：用户说"小臂，最近有哪些人盖过章？"**
```
调用 query_audit_logs → 返回盖章日志列表 → 告知用户
```

---

## 四、后端 API 接口

以下接口供 Dify 工作流调用，获取数据库数据。

### 基础信息

- **Base URL**: `http://127.0.0.1:5001`
- **认证**: 请求时需带 Cookie（先调用 `/api/auth/login` 登录）
- **推荐做法**: 在 Dify 工作流中用 HTTP 请求节点调用这些接口

---

### 4.1 查询请假历史 `GET /api/voice/tools/query_leave_history`

**参数**：
- `name`（可选）：学生姓名，不传则返回最近 10 条

**示例请求**：
```
GET http://127.0.0.1:5001/api/voice/tools/query_leave_history?name=张三
```

**响应**：
```json
{
  "data": [
    {
      "student_name": "张三",
      "dept": "计算机系",
      "leave_type": "病假",
      "start_date": "2026-05-10",
      "end_date": "2026-05-11",
      "status": "APPROVED"
    }
  ]
}
```

**无数据时**：
```json
{"data": []}
```

---

### 4.2 查询盖章日志 `GET /api/voice/tools/query_audit_logs`

**参数**：无

**示例请求**：
```
GET http://127.0.0.1:5001/api/voice/tools/query_audit_logs
```

**响应**：
```json
{
  "data": [
    {
      "timestamp": "2026-05-19 10:30:12",
      "operator_id": "operator1",
      "doc_type": "leave",
      "result": "APPROVED"
    },
    {
      "timestamp": "2026-05-18 15:22:10",
      "operator_id": "voice",
      "doc_type": "leave",
      "result": "REJECT"
    }
  ]
}
```

**无数据时**：
```json
{"data": []}
```

---

### 4.3 智能盖章 `POST /api/stamp/leave`

**说明**：SSE 流式接口，Dify 暂不支持 SSE，建议通过后端直接调用此接口或用 webhook 中转。

**请求体**：空

**返回（SSE 格式）**：
```
event: result
data: {"success": true, "decision": "PASS", "application_id": "LEAVE-20260519-0001", "message": "核验通过"}

event: log
data: {"log": "开始处理请假条盖章..."}
```

**返回字段说明**：
- `success`: 是否成功
- `decision`: PASS / REVIEW / REJECT
- `application_id`: 申请编号（如核验通过）
- `message`: 结果说明

---

### 4.4 获取请假申请列表 `GET /api/leave-applications`

**参数**：
- `status`（可选）：SUBMITTED / APPROVED / REJECTED / STAMPED

**示例请求**：
```
GET http://127.0.0.1:5001/api/leave-applications?status=APPROVED
```

**响应**：
```json
[
  {
    "id": 1,
    "application_id": "LEAVE-20260519-0001",
    "student_name": "张三",
    "student_id": "20230001",
    "dept": "计算机系",
    "leave_type": "病假",
    "start_date": "2026-05-20",
    "end_date": "2026-05-21",
    "reason": "身体不适",
    "status": "APPROVED",
    "approved_by": "AI_AUTO",
    "approved_at": "2026-05-19T10:00:00",
    "ai_comment": "The leave is for 2 days...",
    "created_at": "2026-05-19T09:00:00"
  }
]
```

---

## 五、语音识别（ASR）

### 接口

```
POST /api/voice/asr
Content-Type: audio/webm
Body: [音频二进制数据]
```

**音频格式**：webm（浏览器录音默认格式）
**采样率**：16kHz

**响应**：
```json
{"text": "小臂帮我盖个章"}
```

---

## 六、语音合成（TTS）

### 接口

```
POST /api/voice/tts
Content-Type: application/json

{"text": "机械臂已回到中位"}
```

**响应**：audio/mpeg 二进制音频数据

---

## 七、Dify 接入建议

### 方案 A：后端转发（推荐）

Dify 工作流只做语音理解和对话生成，实际工具调用仍走当前后端：

1. Dify 工作流接收用户语音（文字输入）
2. 理解意图，调用后端 HTTP 接口获取数据
3. 生成自然回复

### 方案 B：Dify 直接调用

若 Dify 需要直接操作数据库：

1. **查询请假记录**：调用 `GET /api/leave-applications`
2. **查询日志**：调用 `GET /api/voice/tools/query_audit_logs`
3. **盖章**：调用 `POST /api/stamp/leave`（需处理 SSE 返回）

### 工具映射建议

| Dify 工具 | 对应后端接口 |
|---|---|
| 查询请假 | `GET /api/voice/tools/query_leave_history` |
| 查询盖章日志 | `GET /api/voice/tools/query_audit_logs` |
| 智能盖章 | `POST /api/stamp/leave` |
| 机械臂控制 | 暂无 HTTP 接口，需保留后端 `_execute_tool` |

### 机械臂控制说明

`arm_home`、`arm_move`、`arm_greet` 三个机械臂控制工具涉及串口通信，暂不适合移到 Dify。建议：

- **Dify 输出控制指令文本**，后端解析后执行
- 或**保留当前后端工具调用机制**，Dify 只负责对话生成

---

## 八、当前 SYSTEM_PROMPT 参考

```
你是机械臂语音助手，名叫小臂。用户通过语音和你对话。

你可以调用的工具：
- arm_home: 回中位
- arm_move: 移动到指定位置
- arm_greet: 打招呼动作
- stamp_leave_check: 智能盖章（自动拍照、扫码、核验、盖章）
- query_leave_history: 查询历史请假记录（可按姓名搜索）
- query_audit_logs: 查询最近的盖章操作日志

规则：
- 你先根据用户意图调用工具，再根据工具返回结果生成自然的语音回复
- 回复要简短自然，像朋友聊天，不要太机械
- 用户问历史记录时，用 query_leave_history 查询后自然地告诉结果
- 用户问盖章记录时，用 query_audit_logs 查询后告诉结果
- 如果盖章核验通过，你要先说"好的，我现在就盖章"，调用工具后再说"盖章完成啦"
- 如果核验不通过，用工具返回的原因自然地告诉用户为什么不能盖章
- 如果用户没放请假条或者扫不到码，提示用户放好请假条再试
- 不可重复盖章
```

---

## 九、状态说明

| 状态 | 含义 |
|---|---|
| SUBMITTED | 已提交，等待审批 |
| APPROVED | 审批通过 |
| REJECTED | 审批拒绝 |
| STAMPED | 已盖章 |
| CANCELLED | 已取消 |

---

## 十、注意事项

1. **认证**：调用 `/api/voice/*` 接口需要先登录获取 Cookie
2. **跨域**：若 Dify 与后端不在同端口，需后端配置 CORS
3. **SSE**：盖章接口返回 SSE 流式数据，Dify HTTP 节点需能解析
4. **串口**：机械臂控制（arm_home / arm_move / arm_greet）需要串口，不适合 Dify 直接调用

---

## 十一、示例对话

| 用户说 | 期望行为 |
|---|---|
| "小臂回中位" | 调用 arm_home → 回复"好的，机械臂已回到中位" |
| "小臂打个招呼" | 调用 arm_greet → 回复"好的，手腕抬起又放下啦" |
| "帮我盖个章" | 调用 stamp_leave_check → 根据结果回复 |
| "张三有没有请假记录" | 调用 query_leave_history(name="张三") → 回复记录 |
| "最近盖了哪些章" | 调用 query_audit_logs → 回复日志列表 |
| "机械臂移到 1500, 1000, 2000" | 调用 arm_move → 回复"已移动到指定位置" |