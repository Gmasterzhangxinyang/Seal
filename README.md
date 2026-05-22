<p align="center">
  <h1 align="center">MEC202 — Intelligent Document Verification & Stamping Robot</h1>
  <img src="docs/logo.png" alt="Logo" width="100%">
</p>

<p align="center">
  <strong>Course Project MEC202 · SPECIFIC GENERAL PROJECT 9</strong><br>
  A robot server for self service of documentation<br>
  Supervisor: Bangxiang Chen (Bangxiang.chen@xjtlu.edu.cn)<br>
  Maintenance branch: <code>wene</code> · Version v1.0 · Last updated: 2026-05-22<br>
  Live URL: <a href="http://110.42.229.174">http://110.42.229.174</a>
</p>

---

## Table of Contents

**User Guide**
1. [System Overview](#1-system-overview)
2. [Access & Login](#2-access--login)
3. [Interface Overview](#3-interface-overview)
4. [Stamping Console](#4-stamping-console)
5. [Leave Application Management](#5-leave-application-management)
6. [Manual Review](#6-manual-review)
7. [Template Management](#7-template-management)
8. [Audit Log](#8-audit-log)
9. [User Management](#9-user-management)
10. [Robotic Arm Calibration](#10-robotic-arm-calibration)
11. [Voice Control](#11-voice-control)
12. [Statistics Dashboard](#12-statistics-dashboard)
13. [FAQ](#13-faq)

**Technical Reference**
14. [System Architecture](#14-system-architecture)
15. [OCR Solution: GLM-4V API Integration](#15-ocr-solution-glm-4v-api-integration)
16. [Deployment Architecture](#16-deployment-architecture)
17. [API Documentation](#17-api-documentation)
18. [Project File Structure](#18-project-file-structure)
19. [Team Roles](#19-team-roles)

---

## 1. System Overview

This system is an **intelligent document verification and stamping robot** designed for university administration scenarios. Core capabilities:

- **Document Scanning & OCR**: Captures images via camera and automatically extracts document content through GLM-4V API
- **Rule-Based Verification**: Automatically validates document fields (required fields, format, type, etc.) against template rules
- **Robotic Arm Stamping**: WeArm 6-DOF robotic arm automatically positions and stamps documents after verification passes
- **Manual Review Loop**: Documents that fail automatic verification enter a review queue for administrator approval
- **Full Leave Application Workflow**: Online submission → Reviewer approval → Download QR-code-secured PDF → Print → Camera verification & stamping
- **Audit Trail**: Every operation records before/after photos, operator, and timestamp

### User Roles & Permissions

| Role | Username | Password | Access |
|------|----------|----------|--------|
| **Admin** | `admin` | `admin123` | All features: stamping, leave, review, templates, users, calibration, stats |
| **Operator** | `operator` | `operator123` | Stamping console, submit leave applications, view own applications |
| **Reviewer** | `reviewer` | `reviewer123` | Stamping console, approve leave, manual review, view audit log |

---

## 2. Access & Login

### 2.1 Access URL

Open `http://110.42.229.174` in your browser to access the login page.

### 2.2 Login

1. Enter your username and password
2. Click **Login**
3. You will be redirected to the main console

### 2.3 Registration

Click **Register** on the login page. Fill in username, email, and password. New users default to the operator role; admins must upgrade roles manually.

### 2.4 Logout

Click the logout icon at the bottom of the sidebar.

---

## 3. Interface Overview

### 3.1 Sidebar Navigation

The left sidebar provides navigation. It can be collapsed to show only icons.

| Group | Menu Items | Access |
|-------|-----------|--------|
| **Common** | Console, Leave Applications | Everyone |
| **Review** | Audit Log, Manual Review | Admin, Reviewer |
| **Admin** | Template Management, User Management, Statistics, Calibration | Admin only |

### 3.2 Language Switch

Click the **English / 中文** button at the bottom of the sidebar to switch UI language.

### 3.3 Connection Status

The dot next to the sidebar title shows backend connection status:
- **Green**: Connected
- **Yellow (flashing)**: Reconnecting
- **Red**: Disconnected

### 3.4 Page Layout

- **Console page**: Wide layout — camera feed on the left, operation panel on the right
- **Other pages**: Centered layout, max width 1200px

---

## 4. Stamping Console

The console is the core page at `/`. It provides **General Stamping** and **Leave Stamping** modes.

### 4.1 Camera Feed

The console displays a live MJPEG video stream from the USB camera. Place the A4 document flat under the camera.

### 4.2 General Document Stamping

For non-leave documents (certificates, forms, etc.), verified against template rules.

1. Place the document under the camera
2. Ensure **General** mode is selected
3. Click **Stamp**
4. The system automatically: captures photo → GLM-4V OCR → rule verification
5. Pass → robotic arm stamps → shows result
6. Fail → document enters manual review queue

### 4.3 Leave Stamping (SSE Streaming)

Leave stamping uses Server-Sent Events for real-time progress display.

1. Place the printed leave form (with QR code) under the camera
2. Switch to **Leave** mode
3. Click **Stamp**
4. The system executes in real-time via SSE:

   ```
   ① Capturing photo…
   ② Scanning QR code → parsing application_id
   ③ GLM-4V vision recognition → extracting student ID, name, date, etc.
   ④ 10 verification checks:
      - QR code signature verification (HMAC-SHA256)
      - Application record existence
      - Status check (must be APPROVED)
      - Duplicate stamping detection
      - Student ID / Name / Type / Date consistency
      - OCR confidence assessment
   ⑤ Pass → robotic arm stamps → status updates to STAMPED
   ⑥ Suspect → enters manual review queue
   ```

5. Final result and before/after photos are displayed

---

## 5. Leave Application Management

Leave applications follow a complete **online approval + physical stamping** workflow.
[See also: Leave Application Flow](docs/leave-application-flow.md) | [Leave Summary](docs/leave-summary.md)

### 5.1 Leave List (`/applications`)

- **Admin/Reviewer**: View all applications
- **Operator**: View only own applications

### 5.2 New Application (`/applications/new`)

Any logged-in user can submit. Fill in: student ID, name, department, leave type (sick/personal/other), start date, end date, and reason.

### 5.3 Approval (Admin/Reviewer only)

On the detail page, click **Approve** or **Reject**. Approved applications generate a QR code with HMAC-SHA256 anti-tampering signature.

### 5.4 Download PDF

After approval, download the PDF with QR code and print it for physical stamping.

### 5.5 Status Flow

```
SUBMITTED ──approved──→ APPROVED ──stamped──→ STAMPED
     │                      │
     └──rejected──→ REJECTED └──failed──→ review queue
```

---

## 6. Manual Review

When automatic verification is inconclusive (low OCR confidence, partial field matches), documents enter the manual review queue.

### 6.1 Access

Admin and Reviewer only. Path: `/review`.

### 6.2 Review Process

1. Switch to **Pending** tab
2. Click an item to see: document photo, OCR fields, check statuses, failure reasons
3. Click **Approve** or **Reject**
4. Approval triggers stamping; rejection records the reason

---

## 7. Template Management

Admin only. Path: `/admin/templates`.

- **List**: All templates with name, type, field count, last updated
- **Create**: Define template name and fields (name, display name, OCR regex, required, validation rules)
- **Edit/Delete**: Modify or remove templates
- **Export**: Export as JSON for backup

---

## 8. Audit Log

Admin and Reviewer only. Path: `/logs`.

Displays every stamping operation: timestamp, operator, document type, result, before/after photos.

---

## 9. User Management

Admin only. Path: `/admin/users`.

View all registered users, delete accounts (admin cannot delete themselves). Role changes require database-level operations.

---

## 10. Robotic Arm Calibration

Admin only. Path: `/calibration`.
[See also: ARM Servo Info](docs/arm-servo-info.md)

### 10.1 Single Servo Control

6 independent sliders for real-time servo angle control.

### 10.2 Quick Positioning

Preset position buttons for automatic arm movement.

### 10.3 Four-Corner Calibration

1. Move arm to each corner of the stamping area
2. Save each corner position
3. System calculates bilinear interpolation coordinates

### 10.4 Homing

Click **Home** to return to initial position.

---

## 11. Voice Control

The console integrates voice control (ASR + TTS).
[See also: Voice Agent](docs/voice-agent.md) | [Voice Dify Design](docs/voice-dify-design.md)

- Click the microphone button to start voice input
- Supported commands: "stamp", "leave mode", "general mode"
- Results are announced via TTS

---

## 12. Statistics Dashboard

Admin only. Path: `/stats`.

Displays: daily stamp count, pass/review/reject rates, document type distribution, operator workload.

---

## 13. FAQ

**Q1: No response after clicking stamp?**
Check the connection status dot. Red means disconnected. Verify: robot machine is on, WireGuard VPN is connected, FastAPI is running.

**Q2: Camera shows black screen?**
Ensure USB camera is connected, no other program is using it, and try refreshing the page.

**Q3: "Invalid QR code" during leave stamping?**
Use only the printed PDF from an approved application. The QR code must be clear and intact.

**Q4: Low OCR accuracy?**
Ensure the document is flat with even lighting. Adjust OCR regex patterns in Template Management.

**Q5: How to view before/after photos?**
Shown directly on the console after stamping. Also available in the Audit Log page.

**Q6: Can operators see the review queue?**
No. The review queue is only visible to admins and reviewers.

---

## 14. System Architecture

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + TailwindCSS + shadcn/ui + Zustand |
| Backend | FastAPI + SQLAlchemy + MySQL |
| OCR | GLM-4V API (Zhipu AI) — remote API, not locally deployed |
| Hardware | WeArm serial robotic arm (ST3215 protocol, 6 servos) |
| Vision | OpenCV + QR code scanning |
| Notifications | Hermes Agent Webhook → Feishu / WeChat |
| Build | Turborepo monorepo + pnpm workspace |

[See also: Tech Stack & Configuration](docs/tech-stack-and-configuration.md) | [SEAL System Overview](docs/seal-stamping-robot-system.md)

### Data Flow

```
Camera capture → QR scan → GLM-4V API remote OCR
  → Rule engine verification (required fields, type, format)
  → [Pass] → Robotic arm stamps → Save audit log
  → [Fail] → Create manual review queue → Review pass → Stamp
```

---

## 15. OCR Solution: GLM-4V API Integration

### Why API instead of local model?

- The robot machine (Windows) has limited compute; cannot run large VLMs
- API latency is acceptable (2-5s/call), suitable for stamping scenarios
- GLM-4V outperforms PaddleOCR on Chinese document tables and field recognition
- No need to maintain local GPU environment and model updates

### Configuration

Set in `.env`:

```env
ZHIPU_API_KEY=your-zhipu-api-key
VLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
VLM_MODEL=glm-4.6v
```

### Call Flow

`apps/backend/vision/ocr.py` wraps the GLM-4V API:

1. Camera captures image
2. Image encoded to base64
3. Prompt sent to GLM-4V API
4. Response parsed to extract fields
5. Returns `{field_name: value, confidence: score}`

### Fallback

PaddleOCR is available as a degraded fallback when GLM-4V API is unavailable.

---

## 16. Deployment Architecture

```
User Browser
        │
        ▼
┌─────────────────────────────────────────┐
│  Cloud Server (110.42.229.174)          │
│  Ubuntu 24.04                            │
│                                          │
│  Nginx :80                               │
│  ├─ /          → Frontend static files   │
│  ├─ /api/*     → WireGuard proxy         │
│  ├─ /api/stamp/leave → SSE streaming     │
│  └─ /video_feed → MJPEG video stream    │
│                                          │
│  Frontend: /var/www/mec202-web/          │
│  Source: /home/ubuntu/MEC202/            │
└──────────────┬──────────────────────────┘
               │ WireGuard VPN
               │ 10.66.66.1 ⇄ 10.66.66.2
               ▼
┌─────────────────────────────────────────┐
│  Robot Machine (Windows)                 │
│                                          │
│  FastAPI :5001                           │
│  ├─ /api/stamp          Stamping         │
│  ├─ /api/stamp/leave     SSE stamping    │
│  ├─ /api/voice/*        Voice control    │
│  ├─ /api/calibration     Calibration     │
│  ├─ /api/logs            Audit log       │
│  ├─ /api/review/*        Manual review   │
│  └─ /video_feed          Camera stream   │
│                                          │
│  Hardware: WeArm arm + USB camera        │
└─────────────────────────────────────────┘
```

[See also: Deployment Guide](docs/deployment.md)

### Port Mapping

| Service | Location | Port | Description |
|---------|----------|------|-------------|
| Nginx Frontend | Cloud Server | 80 | Public entry point |
| FastAPI Backend | Robot Machine | 5001 | Proxied via WireGuard |
| WireGuard | Cloud Server | 51820/UDP | VPN tunnel |
| Vite Dev | Local | 5173 | Hot reload dev server |

---

## 17. API Documentation

FastAPI auto-generated interactive docs: `http://127.0.0.1:5001/docs`

### Main Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/login` | Login | Public |
| POST | `/api/auth/register` | Email registration | Public |
| GET | `/api/auth/me` | Current user info | Authenticated |
| POST | `/api/stamp` | General stamping | Authenticated |
| POST | `/api/stamp/leave` | Leave SSE streaming stamping | Authenticated |
| GET | `/api/cameras` | Camera list | Authenticated |
| GET | `/api/cameras/video_feed` | MJPEG video stream | Authenticated |
| GET | `/api/logs` | Audit log | admin/reviewer |
| GET | `/api/review/pending` | Pending review list | admin/reviewer |
| POST | `/api/review/{id}/resolve` | Resolve review | admin/reviewer |
| GET/POST | `/api/templates` | Template list/create | admin |
| PUT/DELETE | `/api/templates/{id}` | Update/delete template | admin |
| GET | `/api/leave-applications` | Leave application list | Authenticated |
| POST | `/api/leave-applications` | Create leave application | Authenticated |
| POST | `/api/leave-applications/{id}/approve` | Approve application | admin/reviewer |
| POST | `/api/leave-applications/{id}/reject` | Reject application | admin/reviewer |
| GET | `/api/leave-applications/{id}/download` | Download PDF | Authenticated |
| GET | `/api/stats/data` | Statistics data | admin |
| POST | `/api/calibration/move_single` | Servo control | admin |
| GET | `/api/calibration/config` | Calibration config | admin |
| POST | `/api/voice/chat` | Voice control | Authenticated |
| POST | `/api/voice/asr` | Speech recognition | Authenticated |
| POST | `/api/voice/tts` | Text-to-speech | Authenticated |
| GET | `/api/users` | User list | admin |
| DELETE | `/api/users/{username}` | Delete user | admin |

---

## 18. Project File Structure

```
MEC202/
├── apps/
│   ├── backend/
│   │   ├── api/              # FastAPI routes
│   │   │   ├── main.py       # SPA mount + main API
│   │   │   ├── stamp.py      # Stamping flow + SSE
│   │   │   ├── leave_applications.py  # Leave approval
│   │   │   ├── voice.py      # Voice control
│   │   │   ├── review.py     # Manual review
│   │   │   └── templates.py  # Template CRUD
│   │   ├── database/         # SQLAlchemy models
│   │   ├── vision/           # OCR (GLM-4V API) + QR + Camera
│   │   ├── hardware/         # WeArm robotic arm control
│   │   ├── validator/        # Rule engine + 10-check verification
│   │   ├── integration/      # External integrations (DMS, etc.)
│   │   ├── services/         # Notification service
│   │   ├── config.py         # Global configuration
│   │   └── main.py           # Application entry point
│   └── web/                  # React frontend
│       └── src/
│           ├── pages/        # Page components
│           ├── components/   # UI components
│           ├── stores/       # Zustand state management
│           └── i18n/         # Chinese/English i18n
├── docs/                     # Project documentation
├── simulation/               # Robotic arm simulation
├── pnpm-workspace.yaml
└── turbo.json
```

---

## 19. Team Roles

| Role | Modules | Key Deliverables |
|------|---------|-----------------|
| Hardware | Framework + Arm tuning | Accurate stamping, auto calibration |
| Vision | OCR + Camera + Classification | GLM-4V API integration, field extraction accuracy ≥ 90% |
| Logic | Verification rules + Template system | Template CRUD + 10-check verification + dynamic extraction |
| Frontend | React SPA + API integration | Full-featured pages, bilingual UI, camera feed |
| Integration | API layer + Main flow + Testing | End-to-end workflow |

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Deployment Guide](docs/deployment.md) | Prerequisites, installation, configuration, startup |
| [Tech Stack & Configuration](docs/tech-stack-and-configuration.md) | Full technology stack details and configuration reference |
| [SEAL System Overview](docs/seal-stamping-robot-system.md) | System design and architecture overview |
| [Software Prototype User Guide](docs/software-prototype-user-guide.md) | Detailed user manual with screenshots |
| [Leave Application Flow](docs/leave-application-flow.md) | Leave approval workflow and permissions |
| [Leave Summary](docs/leave-summary.md) | Complete leave stamping technical summary |
| [Leave Request Stamping](docs/leave-request-stamping.md) | Leave request stamping deep dive |
| [Voice Agent](docs/voice-agent.md) | Voice control system design |
| [Voice Dify Design](docs/voice-dify-design.md) | Dify workflow integration for voice |
| [ARM Servo Info](docs/arm-servo-info.md) | WeArm servo specifications and control |
| [Full Project Documentation](docs/full-project-documentation.md) | Comprehensive project documentation |

---

*Turborepo Monorepo · React 19 · FastAPI · GLM-4V API · WeArm · WireGuard*
