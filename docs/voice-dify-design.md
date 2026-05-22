# Voice Control Module - Dify Workflow Design Document

> This document is for Dify development, describing the voice module capabilities and the backend API interfaces to be called.

---

## 1. Feature Overview

The voice module allows users to control the robotic arm via voice to perform actions such as greeting, stamping, and querying leave records.

### Three Main Features

| Feature | Interface | Description |
|---|---|---|
| **Voice Chat + Tool Invocation** | `POST /api/voice/chat` | Voice understanding → call tool → natural response |
| **Speech Recognition (ASR)** | `POST /api/voice/asr` | Audio → text (Alibaba Cloud Fun-ASR) |
| **Text-to-Speech (TTS)** | `POST /api/voice/tts` | Text → audio (Fish Audio) |

---

## 2. Voice Chat Tools

The voice assistant (Xiao Bi) can invoke the following tools:

### Tool List

| Tool Name | Description | Parameters |
|---|---|---|
| `arm_home` | Return robotic arm to home position (all servos to zero) | None |
| `arm_move` | Move robotic arm to specified position | `servos`: {PWM values 500-2500 for servos 0-5} |
| `arm_greet` | Greeting action (wrist raises then lowers) | None |
| `stamp_leave_check` | Smart stamping (photo → scan → recognize → verify → stamp) | None |
| `query_leave_history` | Query historical leave records | `name`: Student name (optional) |
| `query_audit_logs` | Query recent stamping operation logs | None |

### Tool Response Examples

```
arm_home → "Robotic arm has returned to home position"
arm_greet → "Greeting action completed, wrist raised and lowered"
stamp_leave_check → "Verification passed, application ID: LEAVE-20260519-0001"
stamp_leave_check → "Verification failed (REJECT). Reason: Student ID mismatch"
query_leave_history → "Leave records:\nZhang San (Computer Science Department) sick leave, 2026-05-10 to 2026-05-11, Status: APPROVED"
query_audit_logs → "Recent stamping records:\n2026-05-19 10:30:12, operator1, leave, Result: APPROVED"
```

---

## 3. Conversation Flow

```
User speaks → ASR recognizes text → Call /voice/chat → Return response text → TTS synthesizes speech
```

### Typical Conversation Scenarios

**Scenario 1: User says "Xiao Bi, return to home position"**
```
Call arm_home → "Robotic arm has returned to home position" → Inform user
```

**Scenario 2: User says "Xiao Bi, help me stamp"**
```
Call stamp_leave_check → Return verification result → Inform user whether stamping was successful
```

**Scenario 3: User says "Xiao Bi, help me check Zhang San's leave records"**
```
Call query_leave_history(name="张三") → Return leave record list → Inform user
```

**Scenario 4: User says "Xiao Bi, who has been stamped recently?"**
```
Call query_audit_logs → Return stamping log list → Inform user
```

---

## 4. Backend API Interfaces

The following interfaces are for Dify workflow calls to retrieve database data.

### Basic Information

- **Base URL**: `http://127.0.0.1:5001`
- **Authentication**: Requests require a Cookie (log in first via `/api/auth/login`)
- **Recommended approach**: Use HTTP request nodes in Dify workflows to call these interfaces

---

### 4.1 Query Leave History `GET /api/voice/tools/query_leave_history`

**Parameters**:
- `name` (optional): Student name. If not provided, returns the most recent 10 records.

**Example Request**:
```
GET http://127.0.0.1:5001/api/voice/tools/query_leave_history?name=张三
```

**Response**:
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

**No Data**:
```json
{"data": []}
```

---

### 4.2 Query Stamping Logs `GET /api/voice/tools/query_audit_logs`

**Parameters**: None

**Example Request**:
```
GET http://127.0.0.1:5001/api/voice/tools/query_audit_logs
```

**Response**:
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

**No Data**:
```json
{"data": []}
```

---

### 4.3 Smart Stamping `POST /api/stamp/leave`

**Description**: SSE streaming interface. Dify does not currently support SSE. It is recommended to call this interface directly through the backend or use a webhook relay.

**Request Body**: Empty

**Response (SSE format)**:
```
event: result
data: {"success": true, "decision": "PASS", "application_id": "LEAVE-20260519-0001", "message": "Verification passed"}

event: log
data: {"log": "Starting leave form stamping process..."}
```

**Response Field Descriptions**:
- `success`: Whether successful
- `decision`: PASS / REVIEW / REJECT
- `application_id`: Application ID (if verification passed)
- `message`: Result description

---

### 4.4 Get Leave Application List `GET /api/leave-applications`

**Parameters**:
- `status` (optional): SUBMITTED / APPROVED / REJECTED / STAMPED

**Example Request**:
```
GET http://127.0.0.1:5001/api/leave-applications?status=APPROVED
```

**Response**:
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

## 5. Speech Recognition (ASR)

### Interface

```
POST /api/voice/asr
Content-Type: audio/webm
Body: [Audio binary data]
```

**Audio Format**: webm (browser recording default format)
**Sample Rate**: 16kHz

**Response**:
```json
{"text": "Xiao Bi, help me stamp"}
```

---

## 6. Text-to-Speech (TTS)

### Interface

```
POST /api/voice/tts
Content-Type: application/json

{"text": "Robotic arm has returned to home position"}
```

**Response**: audio/mpeg binary audio data

---

## 7. Dify Integration Recommendations

### Option A: Backend Relay (Recommended)

The Dify workflow only handles voice understanding and dialogue generation. Actual tool calls still go through the current backend:

1. Dify workflow receives user voice (text input)
2. Understands intent, calls backend HTTP interface to retrieve data
3. Generates natural response

### Option B: Direct Dify Calls

If Dify needs to directly access the database:

1. **Query leave records**: Call `GET /api/leave-applications`
2. **Query logs**: Call `GET /api/voice/tools/query_audit_logs`
3. **Stamping**: Call `POST /api/stamp/leave` (requires handling SSE response)

### Tool Mapping Recommendations

| Dify Tool | Corresponding Backend Interface |
|---|---|
| Query leave | `GET /api/voice/tools/query_leave_history` |
| Query stamping logs | `GET /api/voice/tools/query_audit_logs` |
| Smart stamping | `POST /api/stamp/leave` |
| Robotic arm control | No HTTP interface available, backend `_execute_tool` must be retained |

### Robotic Arm Control Notes

The three robotic arm control tools `arm_home`, `arm_move`, and `arm_greet` involve serial communication and are not suitable for migration to Dify. Recommendations:

- **Dify outputs control instruction text**, backend parses and executes
- Or **retain the current backend tool invocation mechanism**, Dify only handles dialogue generation

---

## 8. Current SYSTEM_PROMPT Reference

```
You are a robotic arm voice assistant named Xiao Bi. Users interact with you via voice.

Tools you can call:
- arm_home: Return to home position
- arm_move: Move to specified position
- arm_greet: Greeting action
- stamp_leave_check: Smart stamping (auto photo, scan, verify, stamp)
- query_leave_history: Query historical leave records (searchable by name)
- query_audit_logs: Query recent stamping operation logs

Rules:
- First call a tool based on user intent, then generate a natural voice response based on the tool's return result
- Responses should be brief and natural, like chatting with a friend, not too robotic
- When users ask about historical records, use query_leave_history to query then naturally present the results
- When users ask about stamping records, use query_audit_logs to query then present the results
- If stamping verification passes, first say "Okay, I'll stamp it now", then after calling the tool say "Stamping is done!"
- If verification fails, use the reason returned by the tool to naturally tell the user why stamping cannot proceed
- If the user hasn't placed a leave form or the code cannot be scanned, prompt the user to place the form properly and try again
- Do not stamp repeatedly
```

---

## 9. Status Descriptions

| Status | Meaning |
|---|---|
| SUBMITTED | Submitted, awaiting review |
| APPROVED | Review approved |
| REJECTED | Review rejected |
| STAMPED | Stamped |
| CANCELLED | Cancelled |

---

## 10. Important Notes

1. **Authentication**: Calling `/api/voice/*` interfaces requires logging in first to obtain a Cookie
2. **Cross-Origin**: If Dify and the backend are not on the same port, the backend needs CORS configuration
3. **SSE**: The stamping interface returns SSE streaming data; the Dify HTTP node must be able to parse it
4. **Serial Port**: Robotic arm control (arm_home / arm_move / arm_greet) requires a serial port and is not suitable for direct Dify calls

---

## 11. Example Conversations

| User Says | Expected Behavior |
|---|---|
| "Xiao Bi, return to home position" | Call arm_home → Respond "Okay, robotic arm has returned to home position" |
| "Xiao Bi, say hi" | Call arm_greet → Respond "Okay, wrist raised and lowered" |
| "Help me stamp" | Call stamp_leave_check → Respond based on result |
| "Does Zhang San have any leave records" | Call query_leave_history(name="张三") → Respond with records |
| "What stamps have been done recently" | Call query_audit_logs → Respond with log list |
| "Move arm to 1500, 1000, 2000" | Call arm_move → Respond "Moved to specified position" |
