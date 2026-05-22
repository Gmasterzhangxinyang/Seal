# Document Verification Auto-Stamping Robot

> **Course Project MEC202 · SPECIFIC GENERAL PROJECT 9**
> A robot server for self service of documentation
> Supervisor: Bangxiang Chen (Bangxiang.chen@xjtlu.edu.cn)
> Maintained branch: `wene` · Last updated: 2026-05-16

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Remote Deployment Architecture](#2-remote-deployment-architecture)
3. [System Architecture (lxx branch)](#3-system-architecturelxx-branch)
4. [Complete Machine Workflow](#4-complete-machine-workflow)
5. [Feature List](#5-feature-list)
6. [Hardware Description](#6-hardware-description)
7. [Software Environment and Installation](#7-software-environment-and-installation)
8. [Quick Start](#8-quick-start)
9. [Remote Connection Solution](#9-remote-connection-solution)
10. [Deployment and Update Process](#10-deployment-and-update-process)
11. [Hermes WeChat Notification Integration](#11-hermes-wechat-notification-integration)
12. [API Documentation](#12-api-documentation)
13. [Project File Structure](#13-project-file-structure)
14. [Configuration Guide](#14-configuration-guide)
15. [Port Mapping Reference](#15-port-mapping-reference)
16. [Troubleshooting](#16-troubleshooting)
17. [Team Division and Timeline](#17-team-division-and-timeline)
18. [Procurement List](#18-procurement-list)
19. [AI Development Assistant (API Integration)](#19-ai-development-assistantapi-integration)

---

## 1. Project Overview

This project builds a **document verification auto-stamping system** based on the WeArm 6-DOF robotic arm. Users place an A4 document under the camera → the system uses OCR to recognize document content → verifies against template rules → upon approval, the robotic arm automatically stamps → generates an audit log. For documents that cannot be automatically verified, the system creates a manual review queue.

### Key Capabilities

- **Intelligent Document Verification**: OCR recognition + rule engine validation, supporting custom templates and field extraction
- **Robotic Auto-Stamping**: WeArm 6-DOF robotic arm with precise positioning for stamping
- **Audit Traceability**: Each stamp generates a structured log including timestamp, operator, document type, and before/after photos
- **Manual Review Closed Loop**: When auto-verification fails, a review queue is created; administrators can view document photos and approve/reject
- **Permission System**: Role isolation (administrator, operator, reviewer) with JWT/session authentication
- **Remote Deployment**: Nginx + WireGuard for public access separated from local hardware

### User Roles

| Role | Responsibilities |
|------|------------------|
| Administrator | System-wide management, user management, role upgrade/downgrade, view all logs |
| Operator | Daily stamping operations, submit document scans |
| Reviewer | Manual review of documents that failed automatic verification |

---

## 2. Remote Deployment Architecture

```
User Browser / WeChat Mini Program
        |
        v
+-----------------------------------------+
|  Cloud Server (XXXXXXX)                 |
|  Ubuntu 24.04                           |
|                                         |
|  Nginx :80                              |
|  +-- /          -> Frontend static files|
|  +-- /api/*     -> WireGuard proxy      |
|  +-- /api/stamp/leave -> SSE streaming  |
|  +-- /video_feed -> MJPEG video stream  |
|                                         |
|  Frontend: /var/www/mec202-web/         |
|  Source: /home/ubuntu/MEC202/           |
+------------------+----------------------+
                   | WireGuard VPN
                   | 10.66.66.1 <-> 10.66.66.2
                   v
+-----------------------------------------+
|  Robot Machine (Windows)                |
|                                         |
|  FastAPI :5001                          |
|  +-- /api/stamp          Stamping       |
|  +-- /api/stamp/leave    SSE streaming  |
|  +-- /api/voice/*        Voice control  |
|  +-- /api/calibration    Calibration    |
|  +-- /api/logs           Audit logs     |
|  +-- /api/review/*       Review         |
|  +-- /video_feed         Camera stream  |
|                                         |
|  Hardware: WeArm robotic arm + USB camera|
+-----------------------------------------+
```

---

## 3. System Architecture (lxx branch)

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + Vite + TypeScript + TailwindCSS + shadcn/ui + Zustand |
| Backend | FastAPI + SQLAlchemy + MySQL |
| OCR | GLM-4V (latest) / PaddleOCR (fallback) |
| Hardware | WeArm serial robotic arm |
| Vision | OpenCV + QR code scanning |
| Notification | Hermes Agent Webhook -> WeChat |
| Build | Turborepo monorepo + pnpm workspace |

### Data Flow

```
Camera capture -> QR scan to extract ID -> GLM-4V OCR field recognition
  -> Rule engine verification (required fields, types, formats)
  -> [Pass] -> Robotic arm stamps -> Save audit log
  -> [Fail] -> Create manual review queue -> Review approved -> Stamp
```

---

## 4. Complete Machine Workflow

```
1. Operator places A4 document flat under the camera
2. Frontend clicks "Scan Document"
3. Camera takes photo, OCR recognizes document content
4. Template rules are invoked for verification:
   - Auto pass -> Live video visible: robot picks up stamp, moves to position, presses to stamp
   - Auto reject -> Submits to "Manual Review" queue, reviewer re-examines then processes again
5. Save before/after stamping photos and operation log
6. Operator retrieves the document
```

---

## 5. Feature List

### Completed

- [x] React SPA + FastAPI frontend/backend separation
- [x] JWT/Cookie dual authentication + permission control
- [x] PaddleOCR (legacy) -> GLM-4V (current) document content recognition
- [x] QR code scanning to extract IDs
- [x] Custom template system + rule engine
- [x] Robotic arm calibration and inverse kinematics stamping
- [x] Joystick teaching + action recording/playback
- [x] MJPEG live video stream
- [x] Audit log + image archiving
- [x] Manual review workflow
- [x] Leave form SSE streaming stamping
- [x] Voice control (ASR + TTS)
- [x] Remote deployment (Nginx + WireGuard + SSE)

---

## 6. Hardware Description

### WeArm Robotic Arm (Current Hardware)

- 6 serial bus servos, based on ST3215 protocol (query reads 7 bytes, response 10 bytes)
- Serial connection, baud rate 115200
- Supports angle control (0-240 degrees) and position control
- End-effector mounted with stamp fixture

### Camera

- USB plug-and-play camera, 1080P
- Auto exposure, auto white balance
- Supports MSMF/DSHOW dual backend auto-adaptation (Windows)

---

## 7. Software Environment and Installation

### Requirements

| Component | Version |
|-----------|---------|
| Python | >= 3.11 |
| Node.js | >= 18 |
| pnpm | >= 9 |
| MySQL | >= 8.0 |

### Installation

```bash
git clone https://github.com/Gmasterzhangxinyang/MEC202
cd MEC202

# Frontend
pnpm install

# Backend
cd apps/backend
pip install -r requirements.txt
# Or use uv: uv sync

# Database
# Start MySQL, create stamp_robot database
alembic upgrade head
```

---

## 8. Quick Start

### Option 1: Turborepo (Recommended)

```bash
pnpm dev     # Starts both frontend Vite + backend Uvicorn simultaneously
```

### Option 2: Manual Start

```bash
# Terminal 1: Backend
cd apps/backend
uvicorn main:app --host 0.0.0.0 --port 5001 --reload

# Terminal 2: Frontend
cd apps/web
pnpm dev
```

### Option 3: Windows Script

```bat
start_dev.bat
```

### Access URLs

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:5001
- Swagger Docs: http://127.0.0.1:5001/docs
- Production: http://XXXXXXX

### Demo Accounts

| Role | Username | Password |
|------|----------|----------|
| Administrator | admin | admin123 |
| Operator | operator | operator123 |
| Reviewer | reviewer | reviewer123 |

---

## 9. Remote Connection Solution

### 9.1 WireGuard VPN Tunnel

**Cloud Server Side (`/etc/wireguard/wg0.conf`):**
```ini
[Interface]
PrivateKey = <cloud server private key>
Address = 10.66.66.1/24
ListenPort = 51820

[Peer]
PublicKey = <robot machine public key>
AllowedIPs = 10.66.66.2/32
```

**Robot Machine Side (Windows WireGuard Client):**
```ini
[Interface]
PrivateKey = <robot machine private key>
Address = 10.66.66.2/24

[Peer]
PublicKey = <cloud server public key>
Endpoint = XXXXXXX:51820
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
```

```bash
# Start
sudo wg-quick up wg0
ping 10.66.66.2   # Verify connectivity
```

### 9.2 Security Group (Tencent Cloud Console)

| Port | Protocol | Direction | Description |
|------|----------|-----------|-------------|
| 51820 | UDP | Inbound | WireGuard |
| 80 | TCP | Inbound | HTTP Frontend |

### 9.3 Nginx Reverse Proxy

Configuration file: `/etc/nginx/sites-enabled/mec202`

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/mec202-web;
    index index.html;

    # React SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # General API proxy
    location /api/ {
        proxy_pass http://10.66.66.2:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # SSE streaming stamping
    location /api/stamp/leave {
        proxy_pass http://10.66.66.2:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;
    }

    # Video stream
    location /video_feed {
        proxy_pass http://10.66.66.2:5001;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    location /api/cameras/video_feed {
        proxy_pass http://10.66.66.2:5001;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

---

## 10. Deployment and Update Process

### 10.1 Frontend Deployment (Cloud Server)

```bash
cd /home/ubuntu/MEC202
git pull origin lxx

cd apps/web
pnpm install && pnpm build

sudo cp dist/index.html /var/www/mec202-web/
sudo cp -r dist/assets/* /var/www/mec202-web/assets/
sudo nginx -s reload
```

### 10.2 Backend Update (Robot Machine)

```bash
cd MEC202
git pull origin lxx
pip install -r requirements.txt   # Or uv sync
# Check .env configuration
# Restart backend: uvicorn main:app --host 0.0.0.0 --port 5001
```

---

## 11. Hermes WeChat Notification Integration

Using Hermes Agent as the unified notification gateway: review/stamp events -> Hermes Webhook -> WeChat notification.

### Event Types

| Event | Trigger Condition |
|-------|-------------------|
| `REVIEW_CREATED` | New manual review arrived |
| `REVIEW_RESOLVED` | Review approved or rejected |
| `AUDIT_APPROVED` | Automatic verification passed and stamped |
| `AUDIT_REJECTED` | Automatic verification rejected |
| `STAMP_COMPLETED` | Stamping completed |
| `SYSTEM_ERROR` | Camera/OCR/robotic arm error |

### Hermes Side Configuration

```bash
hermes gateway setup     # Enable Webhooks + Weixin

hermes webhook subscribe mec202-review \
  --deliver weixin \
  --deliver-only \
  --prompt "[MEC202 Stamping Robot]
Event: {event} | Status: {status} | Document: {doc_type}
Operator: {operator_id} | Review ID: {review_id}
Time: {timestamp}
Message: {message}
Details: {detail}" \
  --description "MEC202 review and notification"

# Test
hermes webhook test mec202-review --payload '{
  "event":"REVIEW_CREATED","status":"pending",
  "doc_type":"leave","operator_id":"operator1",
  "review_id":1,"message":"New leave form requires manual review",
  "detail":"Date exceeds 90 days"
}'
```

### MEC202 Backend Integration

New file `apps/backend/notification/hermes_client.py`:

```python
import logging, requests
from datetime import datetime

logger = logging.getLogger(__name__)

def notify_event(event: str, **kwargs) -> bool:
    from config import HERMES_NOTIFY_ENABLED, HERMES_WEBHOOK_URL
    if not HERMES_NOTIFY_ENABLED or not HERMES_WEBHOOK_URL:
        return False
    payload = {'event': event, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), **kwargs}
    try:
        r = requests.post(HERMES_WEBHOOK_URL, json=payload, timeout=2)
        if r.status_code >= 400:
            logger.warning('Hermes notification failed: status=%s', r.status_code)
            return False
        return True
    except Exception as e:
        logger.warning('Hermes notification exception: %s', e)
        return False
```

Add environment variables in `config.py`:
```python
HERMES_NOTIFY_ENABLED = os.getenv('HERMES_NOTIFY_ENABLED', 'false').lower() == 'true'
HERMES_WEBHOOK_URL = os.getenv('HERMES_WEBHOOK_URL', '')
```

> Notification failures must not block the main business flow.

---

## 12. API Documentation

FastAPI auto-generated interactive documentation: http://127.0.0.1:5001/docs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/register` | Email registration |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Current user |
| GET | `/api/users` | User list (administrator) |
| DELETE | `/api/users/{username}` | Delete user (administrator) |
| POST | `/api/stamp` | Trigger stamping |
| POST | `/api/stamp/leave` | SSE streaming stamping |
| GET | `/api/cameras` | Camera list |
| GET | `/api/cameras/video_feed` | MJPEG video stream |
| GET | `/api/logs` | Audit logs |
| GET | `/api/review/pending` | Pending review list |
| POST | `/api/review/{id}/resolve` | Process review |
| GET | `/api/templates` | Template list |
| POST | `/api/templates` | Create template |
| PUT | `/api/templates/{id}` | Update template |
| DELETE | `/api/templates/{id}` | Delete template |
| GET | `/api/templates/{id}/export` | Export template JSON |
| GET | `/api/stats/data` | Statistics data |
| POST | `/api/calibration/move_single` | Servo control |
| GET | `/api/calibration/config` | Calibration configuration |
| POST | `/api/voice/chat` | Voice control |
| POST | `/api/voice/asr` | Speech recognition |
| POST | `/api/voice/tts` | Text-to-speech |

---

## 13. Project File Structure

```
MEC202/
+-- apps/
|   +-- backend/
|   |   +-- api/              # FastAPI routes
|   |   |   +-- main.py       # SPA mount + main API
|   |   |   +-- stamp.py      # Stamping workflow + SSE streaming
|   |   |   +-- voice.py      # Voice control
|   |   |   +-- review.py     # Manual review
|   |   |   +-- templates.py  # Template CRUD
|   |   |   +-- calibration.py
|   |   |   +-- logs.py
|   |   |   +-- stats.py
|   |   |   +-- users.py
|   |   +-- database/         # SQLAlchemy models + migrations
|   |   +-- vision/           # OCR + QR + camera
|   |   +-- hardware/         # WeArm control
|   |   +-- validator/        # Rule engine
|   |   +-- integration/      # External integrations
|   |   +-- config.py
|   |   +-- main.py           # Application entry point
|   +-- web/                  # React frontend
|       +-- src/
|           +-- pages/
|           +-- components/
|           +-- stores/
|           +-- lib/
+-- doc/                      # Project documentation
+-- pnpm-workspace.yaml
+-- turbo.json
```

---

## 14. Configuration Guide

Key configurations in `apps/backend/config.py`:

```python
ARM_TYPE = 'wearm'            # Robotic arm type
SIMULATION_MODE = False       # Simulation mode (True when no hardware)

# Camera and serial port auto-detection, no manual setup needed
# To manually specify:
# CAMERA_INDEX = 2
# SERIAL_PORT = 'COM9'

# Database
DB_HOST = 'localhost'
DB_PORT = 3306
```

---

## 15. Port Mapping Reference

| Service | Location | Port | Description |
|---------|----------|------|-------------|
| Nginx Frontend | Cloud Server | 80 | Public access entry point |
| FastAPI Backend | Robot Machine | 5001 | Via WireGuard proxy |
| WireGuard | Cloud Server | 51820/UDP | VPN tunnel |
| Hermes Webhook | Cloud Server | 8644 | Internal notification |
| Vite Dev | Local | 5173 | Development hot reload |

---

## 16. Troubleshooting

### Frontend 502
```bash
ping 10.66.66.2                        # Is WireGuard connected
curl http://10.66.66.2:5001/api/health  # Is backend running
sudo wg show                            # Check VPN status
```

### SSE Streaming No Response
Confirm that `/api/stamp/leave` in Nginx includes:
```nginx
proxy_buffering off;
proxy_http_version 1.1;
chunked_transfer_encoding on;
```

### Video Stream Stuttering
Confirm `proxy_buffering off` + `proxy_read_timeout 3600s`.

### WeChat Notifications Not Delivered
```bash
hermes webhook test mec202-review --payload '{...}'
hermes gateway status
```

### Camera Black Screen
Check if the camera is occupied by another program. MSMF/DSHOW auto-adaptation is implemented in config.py.

### Robotic Arm Serial Port Not Found
The system auto-detects CH340 chip. Confirm that `USB-SERIAL CH340` appears in Device Manager.

### Low OCR Recognition Rate
Edit the `ocr_pattern` regex for the corresponding template in the web frontend's `Template Management`.

---

## 17. Team Division and Timeline

| Member | Responsible Module | Core Deliverable |
|--------|-------------------|------------------|
| Hardware | Framework setup + robotic arm tuning | Accurate stamping, auto calibration |
| Vision | OCR + camera + classification | Field extraction accuracy >= 90% |
| Logic | Validation rules + template system | Template CRUD + dynamic extraction |
| Frontend | React SPA + API integration | Full-featured pages, camera working |
| Integration | API layer + main workflow + joint debugging | End-to-end full pipeline |

```
Week 1  Procure hardware -> Build KT board frame -> Wiring + environment setup
Week 2  OCR real form testing + template system + robotic arm tuning
Week 3  React SPA complete + FastAPI API layer complete
Week 4  Joint debugging, end-to-end full pipeline testing
Week 5  Repeated testing with real forms, bug fixes
Week 6  Demo preparation, video recording, report writing
```

---

## 18. Procurement List

| # | Taobao Search Term | Specification | Estimated Price |
|---|-------------------|---------------|-----------------|
| 1 | `Arduino Uno R3 development board official compatible` | Kit with USB cable | ~40 RMB |
| 2 | `MG996R servo metal gear` | 1 piece | ~25 RMB |
| 3 | `MG90S micro servo` | 1 piece | ~15 RMB |
| 4 | `1080P USB camera plug-and-play wide angle` | Plug-and-play | ~60 RMB |
| 5 | `Photosensitive stamp auto-ink custom engraving` | Engraved "APPROVED", 4cm diameter | ~25 RMB |
| 6 | `KT board A3 white 5mm` | 3-5 pieces | ~15 RMB |
| 7 | `Hot glue gun set` | With glue sticks | ~20 RMB |
| 8 | `Dupont wires male-to-female 20cm 40pcs` | 1 pack | ~8 RMB |
| | | **Total** | **~208 RMB** |

---

*Turborepo Monorepo · Python FastAPI · React 19 · GLM-4V · WeArm · WireGuard*

---

## 19. AI Development Assistant (API Integration)

An AI coding assistant is running on the cloud server, accessible via OpenAI-compatible API, helping team members understand and modify server-side code.

### Connection Information

```
Base URL:  http://URL
API Key:   814988d70d320f23cf1dff306e9a8249abcfffaa39459a1f65486d1806522938
Model:     deepseek-v4-pro
```

### Option 1: OpenAI-Compatible Client (Recommended)

Supports OpenWebUI, ChatBox, Continue (VS Code) and any tool compatible with the OpenAI API. Simply fill in the Base URL and API Key above.

### Option 2: curl

```bash
curl -X POST http://URL \
  -H "Authorization: Bearer XXXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-pro",
    "messages": [{"role": "user", "content": "Help me review the route structure in backend/main.py"}]
  }'
```

### Option 3: Python

```python
import requests

resp = requests.post(
    "http://URL",
    headers={"Authorization": "Bearer XXXXXXXXX"},
    json={
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "Explain the inverse kinematics implementation in kinematics.py"}]
    }
)
print(resp.json()["choices"][0]["message"]["content"])
```

### Capabilities

- Read and explain MEC202 source code
- Search files, functions, and code patterns
- Help debug build errors and configuration issues
- Explain project architecture, API endpoints, and deployment setup
- Modify server-side files under `/home/ubuntu/MEC202/`

### Limitations

- Only answers MEC202 project-related questions
- File operations are restricted to `/home/ubuntu/MEC202/`
- Non-project questions will be rejected
