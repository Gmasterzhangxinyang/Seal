# Voice Module Agent

## Core Architecture: LLM as a Function Calling Router

```
User presses and holds to speak
    |
    v
+-----------------------------------------------------+
|                  Dify Voice Q&A Workflow             |
|                                                     |
|  Audio --> ASR --> LLM (Function Calling)            |
|                    |                                 |
|               tool_id 1-4 --> Directly generate comment
|                    |                                 |
|               tool_id 5-6 --> HTTP call to backend to query database
|                                    |                 |
|                               Fill in comment        |
|                                                     |
|  Output: { tool_id, comment }                       |
+-----------------------------------------------------+
                              |
                              v
                   Backend /api/voice/tts
                              |
                              v
                   voice.yml TTS --> Audio --> Frontend playback
```

## Function Calling Mapping

| tool_id | Action | Executor | Description |
|---------|--------|----------|-------------|
| 1 | arm_home | Hardware | Robotic arm returns to home position |
| 2 | arm_move | Hardware | Robotic arm moves to specified position |
| 3 | arm_greet | Hardware | Greeting gesture |
| 4 | stamp_leave_check | Hardware | Smart stamping workflow |
| 5 | query_leave_history | **Backend HTTP** | Query leave application database |
| 6 | query_audit_logs | **Backend HTTP** | Query stamping logs |

## Essential Difference Between the Two Types of Tools

**tool_id 1-4 (Hardware Actions)**: The LLM directly generates a descriptive comment based on the voice intent, with no external calls involved. Execution of the robotic arm is driven by the backend after receiving the tool_id.

**tool_id 5-6 (Database Queries)**: The LLM generates HTTP request parameters -> the Dify HTTP node calls the backend `/api/voice/tools/query_*` -> retrieves real data and fills it into the comment -> then generates a TTS reply.

This separation is well-founded: hardware actions require real-time backend control, while database queries need live data. Leaving the former to the backend and delegating the latter to Dify HTTP nodes ensures each component does what it does best.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/voice/chat` | Audio -> Dify -> `{tool_id, comment}` |
| `POST /api/voice/tts` | Text -> voice.yml -> Audio wav |
| `GET /api/voice/tools/query_leave_history` | Dify HTTP node queries leave application table |
| `GET /api/voice/tools/query_audit_logs` | Dify HTTP node queries stamping logs |

## Demo Examples

**Example 1: Leave Application Query**

User says: "Check whether Zhang San's leave application has been approved"

```
ASR -> "Check whether Zhang San's leave application has been approved"
LLM recognizes -> tool_id = 5 (query_leave_history), name = "Zhang San"
Dify HTTP node -> GET /api/voice/tools/query_leave_history?name=Zhang San
Backend returns -> [{"student_name":"Zhang San","status":"APPROVED",...}]
LLM generates comment -> "Found Zhang San's leave record, May 18 to May 20, sick leave, approved"
voice.yml TTS -> Audio
Frontend playback
```

**Example 2: Greeting**

User says: "Let's say hi"

```
ASR -> "Let's say hi"
LLM recognizes -> tool_id = 3 (arm_greet), no external calls
Directly generates comment -> "Sure, let me greet you"
voice.yml TTS -> Audio
Frontend plays audio + backend simultaneously drives robotic arm to perform wrist raise and lower gesture
```

## Design Considerations

The routing decision of Function Calling is placed in the Dify LLM rather than the backend -- this is the key design choice. The LLM understands natural language and can handle synonymous variations like "robotic arm go home" and "arm going home", which hard-coded regex matching cannot achieve. The backend does not need to understand voice intent; it only needs to execute the corresponding action or query.

However, this also means the backend fully relies on the tool_id returned by Dify -- if the LLM misclassifies, the backend will execute the wrong action. Currently there is no validation on tool_id, which is an area that needs improvement.
