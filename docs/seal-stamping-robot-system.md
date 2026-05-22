# SEAL — Intelligent Stamp Robot System

> **From digital approval to physical stamp — every step verified, every action recorded, every stamp accountable.**
> One seal, full-chain trust.

---

## 1. System Overview

SEAL is a **fully automated leave request verification and stamping robot system** designed for school administrative scenarios.

Core workflow:

```
Student submits leave request online
        ↓
  Admin / AI review and approval
        ↓
  Generate QR code with HMAC signature
        ↓
  Print paper leave request (with QR code)
        ↓
  Offline: place paper → scan & verify → automatic stamp
        ↓
  Full-chain audit trail
```

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Frontend React SPA                        │
│  Console · Leave Application · Admin Panel · Audit Log ·        │
│  Robot Arm Calibration · Voice Control                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                        Backend FastAPI                           │
│  Voice Module · Stamp Module · Leave Application Module ·       │
│  Auth Module · OCR/Vision Module                                │
│                                                                   │
│  /api/voice/chat     — Voice → Dify → Tool execution            │
│  /api/voice/tts      — Text → voice.yml TTS                     │
│  /api/stamp/leave    — Scan → Verify → Stamp                    │
│  /api/leave-applications/* — Leave application CRUD + AI review │
└──────┬─────────────────┬──────────────────┬─────────────────────┘
        │                 │                  │
        ▼                 ▼                  ▼
┌──────────────────┐ ┌───────────┐ ┌─────────────────────────────┐
│  AI Layer — Dify │ │ Hardware  │ │  Data Layer — MySQL + File   │
│                  │ │   Layer   │ │         Storage              │
│ Voice Q&A        │ │  WeArm    │ │  leave_applications table   │
│ workflow         │ │ Robot arm │ │  audit_log table            │
│ app-LsjmYRdK... │ │           │ │  users / personnel table    │
│ ASR + LLM        │ │ USB       │ │  review_queue table         │
│ Function Calling │ │  Camera   │ │  tts_cache/ directory       │
│                  │ │ OpenCV    │ │  audit_images/ directory    │
│ voice.yml TTS    │ │ PaddleOCR │ │                             │
│ app-zyiT0PYF...  │ │  pyzbar   │ │                             │
│ Text → Speech    │ │           │ │                             │
│ synthesis        │ │           │ │                             │
└──────────────────┘ └───────────┘ └─────────────────────────────┘
```

---

## 3. Module Details

### 3.1 Voice Control Module — Xiao Bi

Users can interact with the SEAL system via voice to control the robot arm and query records.

#### Tool Mapping

| tool_id | Action | Executor | Description |
|---|---|---|---|
| 1 | arm_home | WeArm hardware | Return robot arm to home position (center) |
| 2 | arm_move | WeArm hardware | Move to specified position (reserved) |
| 3 | arm_greet | WeArm hardware | Greeting: three-segment bow action + voice confirmation |
| 4 | stamp_leave_check | WeArm hardware | Full smart stamping workflow |
| 5 | query_leave_history | MySQL | Query leave records, supports filtering by name |
| 6 | query_audit_logs | MySQL | Query successful stamp logs |

#### Greeting Action Details (tool_id = 3)

```
Return to center → Bow (s0=center) → s0=1320 → Bow
  → s0=1480 → Bow → s0=1680 → Bow → Return to center
```

Each bow = wrist raise (2200) → lower (PWM_MID[3]=1889), with TTS voice confirmation.

#### Home Position (PWM_MID)

| Servo | PWM | Description |
|---|---|---|
| s0 | 1500 | Base |
| s1 | 2130 | Upper arm |
| s2 | 2123 | Forearm |
| s3 | 1889 | Wrist |
| s4 | 1493 | Gripper |
| s5 | 1500 | Auxiliary |

#### TTS Cache Mechanism

- On startup, pre-generates TTS audio for fixed responses of tool_id 1-4 in the background
- Cached in `api/tts_cache/` directory
- On cache hit, returns directly, skipping Dify TTS call
- On cache miss, synchronously calls Dify voice.yml to generate and cache

#### Voice Pipeline

```
User presses and holds to speak (WebRTC)
        ↓
POST /api/voice/chat (multipart/form-data)
        ↓
Dify voice Q&A workflow
  ASR → text
  LLM → tool_id + comment
        ↓
Backend _execute_tool()
  tool_id 1-4: execute hardware in background thread → return immediately
  tool_id 5-6: query MySQL → LLM summary → wait
        ↓
Return {tool_id, comment, audio: base64?}
        ↓
Frontend playAudioBlob() → play directly
        ↓
If audio is empty, call /api/voice/tts → Dify TTS → play
```

---

### 3.2 Verification & Stamping Module — Stamp

#### Full Verification Workflow

```
POST /api/stamp/leave
        ↓
① Capture before_image (confirm paper is present)
        ↓
② Scan QR code with pyzbar
        ↓
③ HMAC-SHA256 signature verification
        ↓
④ Query leave_applications by application_id
        ↓
⑤ Status check: must be APPROVED, not STAMPED
        ↓
⑥ OCR scan paper leave request (PaddleOCR)
        ↓
⑦ Field extraction: student_name, student_id, leave_type, dates
        ↓
⑧ Student ID consistency check (OCR vs database)
        ↓
⑨ Risk scoring + decision
        ↓
⑩ PASS → capture photo again before stamping (paper position SSIM comparison)
        ↓
⑪ Robot arm stamps (stamp_at)
        ↓
⑫ Capture after_image
        ↓
⑬ Write to audit_log
        ↓
⑭ Return decision result
```

#### Decision Logic

| Decision | Condition | Action |
|---|---|---|
| PASS | All verifications passed, OCR confidence ≥ 0.85 | Auto stamp |
| REVIEW | Some fields uncertain, confidence 0.65-0.85 | Enter manual review |
| REJECT | Signature failed / status abnormal / student ID mismatch / already stamped | Reject stamping |

#### SSIM Paper Position Comparison

Capture another photo before stamping and compare structural similarity (SSIM) with before_image. If paper has shifted noticeably, enter REVIEW instead of stamping directly.

---

### 3.3 Leave Application Module — Leave Application

#### State Machine

```
SUBMITTED → APPROVED → STAMPED
    ↓
  REJECTED
```

| State | Meaning |
|---|---|
| SUBMITTED | Submitted, awaiting review |
| APPROVED | Approved, awaiting offline stamping |
| REJECTED | Rejected |
| STAMPED | Stamping completed |
| CANCELLED | Cancelled |

#### AI Review (Optional)

Leave requests can be automatically reviewed via the Dify review workflow, without manual intervention.

#### QR Signature

```python
payload = {
    "application_id": "LEAVE-20260519-0001",
    "student_id": "20230001",
    "timestamp": "...",
}
sig = HMAC-SHA256(json.dumps(payload), SECRET_KEY)
qr_content = json.dumps(payload) + "." + sig
```

---

### 3.4 Audit Log Module

Every operation record is written to the `audit_log` table:

| Field | Description |
|---|---|
| timestamp | Operation time |
| operator_id | Operator (operator / voice / admin) |
| doc_type | Document type (leave / general) |
| result | Verification result (APPROVED / REJECTED / REVIEW) |
| before_img | Pre-stamp image path |
| after_img | Post-stamp image path |
| application_id | Associated application ID |
| task_id | Associated task ID |
| risk_score | Risk score |
| verification_result | Detailed verification result JSON |

---

### 3.5 Robot Arm Module — WeArm

#### Calibration

Four-corner calibration (TL / TR / BL / BR), saved in `calibration.json`. After calibration, the robot arm can accurately move to any pixel coordinate.

#### Main Interfaces

| Function | Description |
|---|---|
| `move_to({s0:pwm, ...}, duration)` | Move multiple axes simultaneously to specified PWM |
| `move_single(servo_id, pwm, duration)` | Move single axis |
| `stamp_at(position_values)` | Execute stamp: move → press down → return to center |
| `home()` | Return to home position |

#### Simulation Mode

When `SIMULATION_MODE = True`, does not connect to real serial port, used for development and testing.

---

### 3.6 OCR and Vision Module

#### PaddleOCR

- Chinese and English mixed text recognition
- Supports multiple fonts (primarily printed text)
- Confidence score used for decision threshold judgment

#### QR Code Scanning

- Real-time decoding with pyzbar
- Supports QR Code, Data Matrix, and other formats

---

## 4. Frontend Pages

| Path | Page | Description |
|---|---|---|
| `/` | Home | System overview |
| `/stamp` | Console | Scan, verify, and stamp main interface |
| `/voice` | Voice Control | Press and hold to speak, drive hardware |
| `/applications` | Leave Applications | Application list |
| `/applications/new` | New Application | Form submission |
| `/admin` | Admin Panel | User/template/log management |
| `/logs` | Audit Log | Operation history records |
| `/review` | Manual Review | REVIEW task processing |
| `/calibration` | Robot Arm Calibration | Four-corner calibration and save |

---

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Frontend Framework | React 19 + Vite + TypeScript |
| Styling | TailwindCSS v4 |
| State Management | Zustand |
| Routing | React Router v6 |
| Backend Framework | FastAPI (Python 3.11+) |
| Database | MySQL 8.0 + SQLAlchemy + Alembic |
| AI | Dify Workflow (Voice Q&A + TTS + AI Review) |
| OCR | PaddleOCR / PaddlePaddle |
| Image Processing | OpenCV + Pillow + scikit-image (SSIM) |
| QR Code | pyzbar |
| Robot Arm | WeArm Serial (PWM 500-2500) |
| Serial Communication | pyserial |
| Monorepo | Turborepo + pnpm workspaces |

---

## 6. Key Files

### Backend

| File | Description |
|---|---|
| `api/voice.py` | Voice module core: tool execution, TTS cache, LLM summary |
| `api/stamp.py` | Full verification and stamping workflow: QR, OCR, SSIM, stamping |
| `api/leave_applications.py` | Leave application CRUD + review |
| `utils/dify_client.py` | Dify workflow client (voice Q&A + voice.yml TTS) |
| `hardware/wearm.py` | WeArm robot arm driver, PWM_MID home position |
| `vision/ocr.py` | PaddleOCR recognition and field extraction |
| `vision/qr_scanner.py` | pyzbar QR code scanning |
| `calibration.py` | Robot arm four-corner calibration |
| `database/connection.py` | MySQL connection management |

### Frontend

| File | Description |
|---|---|
| `components/voice-control.tsx` | Voice control component, press and hold to speak |
| `pages/StampPage.tsx` | Console main page |
| `pages/LeaveApplicationsPage.tsx` | Leave application list |
| `pages/CalibrationPage.tsx` | Robot arm calibration page |

---

## 7. Dify Application Configuration

| Application | App ID | Purpose |
|---|---|---|
| Voice Q&A Workflow | `app-LsjmYRdKgWnLvI7TdpCs8UcV` | ASR + LLM Function Calling |
| voice.yml TTS | `app-zyiT0PYF7fFDhhXeWZzUsc4N` | Text-to-speech synthesis |
| Leave Request Review Workflow | `app-YLvNXsCxer7Q5VKS0bsjdmit` | AI automatic review of leave reasons |

---

## 8. TTS Cache Details

The `api/tts_cache/` directory stores pre-generated TTS audio files, with filenames in the format `md5(text).wav`.

**Fixed response texts (pre-cached on startup):**

| tool_id | Text |
|---|---|
| 1 | Okay, the robot arm has returned to center position |
| 2 | Okay, the robot arm is moving |
| 3 | Okay, the wrist has been raised and lowered |
| 4 | Okay, starting to stamp now |

---

## 9. API Reference

### Voice Module

| Method | Path | Description |
|---|---|---|
| POST | `/api/voice/chat` | Audio → Dify → Tool execution → Return comment + audio |
| POST | `/api/voice/tts` | Text → voice.yml TTS → Audio WAV |
| GET | `/api/voice/tools/query_leave_history` | Query leave records (supports name parameter) |
| GET | `/api/voice/tools/query_audit_logs` | Query successful stamp logs |

### Stamping Module

| Method | Path | Description |
|---|---|---|
| POST | `/api/stamp/leave` | Full verification and stamping workflow (SSE streaming response) |
| POST | `/api/stamp/verify` | Verify only, no stamping |

### Leave Applications

| Method | Path | Description |
|---|---|---|
| POST | `/api/leave-applications` | Create application |
| GET | `/api/leave-applications` | List (supports status filtering) |
| GET | `/api/leave-applications/{id}` | Details |
| POST | `/api/leave-applications/{id}/approve` | Approve |
| POST | `/api/leave-applications/{id}/reject` | Reject |

### Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Current user |

---

## 10. Quick Start

```bash
# Clone the project
git clone git@github.com:Gmasterzhangxinyang/MEC202.git
cd MEC202

# Install dependencies
pnpm install

# Start development server
pnpm dev
# Frontend: http://localhost:5173
# Backend: http://localhost:5001
```

**Hardware Connection:**

1. Connect USB camera
2. Connect WeArm (CH340 serial port)
3. Set `SIMULATION_MODE = False` (`apps/backend/config.py`)

---

## 11. Demo Accounts

| Account | Password | Role |
|---|---|---|
| admin | admin123 | Administrator |
| operator1 | op123 | Operator |
| reviewer1 | reviewer123 | Reviewer |

---

*SEAL — One Seal. Full Trust.*
