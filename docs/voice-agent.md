# 语音模块 Agent

## 核心架构：LLM 作为 Function Calling 路由器

```
用户按住说话
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                  Dify 语音问答工作流                    │
│                                                     │
│  音频 ──► ASR ──► LLM（Function Calling）            │
│                    │                                 │
│               tool_id 1-4 ──► 直接生成 comment       │
│                    │                                 │
│               tool_id 5-6 ──► HTTP 调后端查库         │
│                                    │                 │
│                               填入 comment          │
│                                                     │
│  Output: { tool_id, comment }                       │
└─────────────────────────────────────────────────────┘
                              │
                              ▼
                   后端 /api/voice/tts
                              │
                              ▼
                   voice.yml TTS ──► 音频 ──► 前端播放
```

## Function Calling 映射

| tool_id | 动作 | 执行者 | 说明 |
|---------|------|--------|------|
| 1 | arm_home | 硬件 | 机械臂回中位 |
| 2 | arm_move | 硬件 | 机械臂移动到指定位置 |
| 3 | arm_greet | 硬件 | 打招呼动作 |
| 4 | stamp_leave_check | 硬件 | 智能盖章流程 |
| 5 | query_leave_history | **后端 HTTP** | 查请假数据库 |
| 6 | query_audit_logs | **后端 HTTP** | 查盖章日志 |

## 两类工具的本质差异

**tool_id 1-4（硬件动作）**：LLM 根据语音意图直接生成描述性 comment，不涉及外部调用。机械臂的执行由后端收到 tool_id 后驱动。

**tool_id 5-6（数据库查询）**：LLM 生成 HTTP 请求参数 → Dify HTTP 节点调用后端 `/api/voice/tools/query_*` → 拿到真实数据填入 comment → 再生成 TTS 回复。

这种分离是合理的：硬件动作需要后端实时控制，数据库查询需要实时数据。把前者留给后端、把后者交给 Dify HTTP 节点，正是各自做自己最擅长的事。

## 端点

| 端点 | 作用 |
|------|------|
| `POST /api/voice/chat` | 音频 → Dify → `{tool_id, comment}` |
| `POST /api/voice/tts` | 文本 → voice.yml → 音频 wav |
| `GET /api/voice/tools/query_leave_history` | Dify HTTP 节点查请假表 |
| `GET /api/voice/tools/query_audit_logs` | Dify HTTP 节点查盖章日志 |

## 演示示例

**示例 1：盖章查询**

用户说："帮我查一下张三的假条有没有批"

```
ASR → "帮我查一下张三的假条有没有批"
LLM 识别 → tool_id = 5（query_leave_history），name = "张三"
Dify HTTP 节点 → GET /api/voice/tools/query_leave_history?name=张三
后端返回 → [{"student_name":"张三","status":"APPROVED",...}]
LLM 生成 comment → "查到张三的请假记录，5月18日到5月20日，病假，已审批通过"
voice.yml TTS → 音频
前端播放
```

**示例 2：打招呼**

用户说："来打个招呼"

```
ASR → "来打个招呼"
LLM 识别 → tool_id = 3（arm_greet），无外部调用
直接生成 comment → "好的，我来打个招呼"
voice.yml TTS → 音频
前端播放音频 + 同时后端驱动机械臂执行手腕抬起放下动作
```

## 设计思考

Function Calling 的路由决策放在 Dify LLM，而不是后端——这是关键选择。LLM 理解自然语言，能处理"机械臂回家"和"臂子回家吗"这种同义变体，而硬编码的正则匹配做不到。后端不需要理解语音意图，只需要执行对应的动作或查询。

但这也意味着后端完全依赖 Dify 返回的 tool_id——如果 LLM 分类错误，后端会执行错误的动作。当前没有对 tool_id 做校验，这是需要改进的地方。
