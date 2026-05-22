# MEC202 Tech Stack & Configuration Summary

## Project Structure

```
MEC202/
├── apps/
│   ├── backend/          # Python FastAPI Backend
│   │   ├── api/          #   Route modules
│   │   ├── database/     #   Data models & connections
│   │   ├── hardware/     #   Robotic arm driver
│   │   ├── validator/    #   Document validation rules
│   │   └── vision/       #   OCR / Camera / Classification
│   └── web/              # React 19 Frontend
│       └── src/
│           ├── pages/    #   Page components
│           ├── stores/   #   Zustand state
│           └── types/    #   TypeScript types
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

---

## Frontend Tech Stack

| Category | Technology | Version |
|------|------|------|
| Framework | React / React DOM | ^19.2.5 |
| Routing | React Router | ^7.15.0 |
| Language | TypeScript | ~6.0.2 |
| Build | Vite | ^8.0.10 |
| Styling | TailwindCSS | ^4.2.4 |
| State Management | Zustand | ^5.0.13 |
| Charts | Recharts | ^3.8.1 |
| Icons | Lucide React | ^1.14.0 |
| Utilities | clsx / tailwind-merge / class-variance-authority | — |
| Linting | ESLint + typescript-eslint | ^10.2.1 / ^8.58.2 |

### Vite Dev Server

```typescript
// apps/web/vite.config.ts
server: { port: 5173 }
proxy: {
  '/api':        'http://127.0.0.1:5001'
  '/video_feed': 'http://127.0.0.1:5001'
}
```

### Frontend Routes

| Path | Page | Access |
|------|------|------|
| `/login` | Login | Public |
| `/register` | Register | Public |
| `/` | Stamp Console | Authenticated users |
| `/logs` | Audit Logs | Authenticated users |
| `/review` | Manual Review | Authenticated users |
| `/stats` | Statistics | Authenticated users |
| `/calibration` | Arm Calibration | Authenticated users |
| `/admin/templates` | Template Management | Admin |
| `/admin/users` | User Management | Admin |

---

## Backend Tech Stack

| Category | Technology | Version |
|------|------|------|
| Language | Python | >= 3.11 |
| Web Framework | FastAPI | >= 0.136.1 |
| ASGI Server | Uvicorn | >= 0.46.0 |
| OCR | PaddleOCR / PaddlePaddle | < 3 |
| Image Processing | OpenCV / Pillow / scikit-image | >= 4.13 / >= 12.2 / >= 0.26 |
| QR Code | pyzbar | >= 0.1.9 |
| Serial Communication | pyserial | >= 3.5 |
| HTTP Client | requests | >= 2.33.1 |
| Password Hashing | Werkzeug | >= 3.1.8 |
| Signing | itsdangerous | >= 2.2.0 |

### FastAPI Application Configuration

```python
# apps/backend/api/main.py
title = "Document Stamp Robot"
version = "2.0"
host = "0.0.0.0"
port = 5001

# CORS
allow_origins = ["http://localhost:5173"]
```

### Backend API Route Modules

| Module | File | Function |
|------|------|------|
| Auth | `api/auth.py` | Login / Register / Token verification |
| Stamp | `api/stamp.py` | Trigger stamp / Review stamp |
| Camera | `api/cameras.py` | Camera list / MJPEG video stream |
| Logs | `api/logs.py` | Audit log queries |
| Review | `api/review.py` | Review queue management |
| Templates | `api/templates.py` | Template CRUD / Export |
| Stats | `api/stats.py` | Operation statistics |
| Calibration | `api/calibration.py` | Arm calibration data |
| Images | `api/images.py` | Image file service |
| Users | `api/users.py` | User management |

---

## Monorepo Configuration

| Item | Configuration |
|------|------|
| Package Manager | pnpm ^9.15.0 |
| Build Orchestration | Turborepo |
| Workspace | `apps/*` |

```json
// turbo.json
{
  "tasks": {
    "dev":    { "cache": false, "persistent": true },
    "build":  { "dependsOn": ["^build"], "outputs": ["dist/**"] },
    "clean":  { "cache": false }
  }
}
```

---

## Database Configuration

### Connection Info

```python
# apps/backend/config.py
DB_HOST     = 'localhost'
DB_PORT     = 3306
DB_USER     = 'stamp_robot'
DB_PASSWORD = 'stamp_robot_pwd'
DB_NAME     = 'stamp_robot'
DATABASE_URL = 'mysql+pymysql://stamp_robot:stamp_robot_pwd@localhost:3306/stamp_robot?charset=utf8mb4'
```

### ORM / Migrations

| Item | Technology |
|------|------|
| ORM | SQLAlchemy >= 2.0 |
| Driver | PyMySQL >= 1.1 |
| Migrations | Alembic >= 1.13 |
| Encryption | cryptography >= 42.0 |

### Database Table Structure

```python
# apps/backend/database/models.py
```

#### personnel — Personnel Information

| Field | Type | Description |
|------|------|------|
| id_number | VARCHAR(20) PK | Student/Employee ID |
| name | VARCHAR(50) | Name |
| dept | VARCHAR(100) | Department |
| role | VARCHAR(50) | Role (student/staff) |

#### users — User Accounts

| Field | Type | Description |
|------|------|------|
| username | VARCHAR(50) PK | Username |
| password_hash | VARCHAR(200) | Werkzeug hash |
| email | VARCHAR(100) UQ | Email |
| role | VARCHAR(20) | Role (admin/operator/reviewer) |
| created_at | VARCHAR(30) | Creation time |

#### doc_templates — Document Templates

| Field | Type | Description |
|------|------|------|
| id | INT PK AUTO | Primary key |
| name | VARCHAR(100) | Template name |
| code | VARCHAR(50) UQ | Template code (leave/expense/cert/general) |
| description | TEXT | Description |
| is_system | INT | System template flag |
| classification_keywords | TEXT | Classification keywords JSON array |
| classification_regex | TEXT | Classification regex |
| sort_order | INT | Sort weight |
| requires_stamp | INT | Whether stamping is required |
| stamp_position | VARCHAR(100) | Preset stamp coordinates "x,y" |
| stamp_keywords | TEXT | Stamp positioning keywords |
| created_at / updated_at | VARCHAR(30) | Timestamps |

#### template_fields — Template Fields

| Field | Type | Description |
|------|------|------|
| id | INT PK AUTO | Primary key |
| template_id | INT FK → doc_templates.id | Parent template |
| field_name | VARCHAR(100) | Field name (name/student ID/date, etc.) |
| field_label | VARCHAR(100) | Display label |
| field_category | VARCHAR(20) | Category: required / optional / forbidden |
| ocr_pattern | TEXT | OCR extraction regex |
| validation_rule | TEXT | Validation rule JSON |
| sort_order | INT | Sort order |

#### template_examples — Template Example Images

| Field | Type | Description |
|------|------|------|
| id | INT PK AUTO | Primary key |
| template_id | INT FK UQ → doc_templates.id | Parent template |
| image_path | VARCHAR(500) | Image path |
| generated_at | VARCHAR(30) | Generation time |

#### audit_log — Audit Logs

| Field | Type | Description |
|------|------|------|
| id | INT PK AUTO | Primary key |
| timestamp | VARCHAR(30) | Operation time |
| operator_id | VARCHAR(50) | Operator |
| doc_type | VARCHAR(50) | Document type |
| qr_content | VARCHAR(500) | QR code content |
| doc_fields | TEXT | Extracted fields JSON |
| ocr_text | TEXT | OCR full text |
| result | VARCHAR(30) | Result (APPROVED/REJECTED/PENDING_REVIEW) |
| errors | TEXT | Error messages |
| before_img / after_img | VARCHAR(500) | Pre/post stamp image paths |
| dms_doc_id | VARCHAR(100) | DMS document ID |

#### review_queue — Manual Review Queue

| Field | Type | Description |
|------|------|------|
| id | INT PK AUTO | Primary key |
| timestamp | VARCHAR(30) | Enqueue time |
| operator_id | VARCHAR(50) | Operator |
| doc_type | VARCHAR(50) | Document type |
| doc_fields | TEXT | Extracted fields |
| ocr_text | TEXT | OCR full text |
| warnings | TEXT | Warning messages |
| image_path | VARCHAR(500) | Image path |
| status | VARCHAR(20) | Status (pending/approved/rejected) |
| reviewer_id | VARCHAR(50) | Reviewer |
| resolved_at | VARCHAR(30) | Resolution time |
| decision | VARCHAR(20) | Review decision |
| stamped | INT | Whether stamped |

### Preset Template Data

| Code | Name | Required Fields | Forbidden Fields |
|------|------|----------|----------|
| leave | Leave Application | Name, Student ID, Date, Reason | Amount |
| expense | Expense Reimbursement | Name, Student ID, Date, Amount | Reason |
| cert | Certificate Application | Name, Student ID, Date | Amount |
| general | General Document | Name, Date | — |

### Preset Accounts

| Username | Password | Role |
|--------|------|------|
| admin | admin123 | admin |
| operator1 | op123 | operator |
| reviewer1 | reviewer123 | reviewer |

---

## Hardware Configuration

### Robotic Arm

```python
# apps/backend/config.py

# Type selection: 'wearm' (Serial) / 'hiwonder' (WiFi)
ARM_TYPE = 'wearm'

# WeArm (CH340 Serial)
SERIAL_BAUD = 115200
SERIAL_PORT = 'Auto-detect'   # CH340 VID:0x1A86 PID:0x7523

# Hiwonder ArmPi (WiFi)
HIWONDER_HOST = '192.168.1.175'
HIWONDER_PORT = 9999
```

### Inverse Kinematics Parameters (WeArm)

```python
ARM_H0 = 20.0    # Vertical distance from base rotation axis to shoulder joint (mm)
ARM_L1 = 103.0   # Upper arm length (mm)
ARM_L2 = 96.0    # Forearm length (mm)
ARM_L3 = 50.0    # Wrist to end effector distance (mm)
```

### Camera

```python
# Auto-detection strategy: iterate index 0-4, test MSMF / DSHOW backends respectively
CAMERA_INDEX    = Auto-detect      # Select the one with highest brightness
CAMERA_BACKEND  = CAP_MSMF or CAP_DSHOW
Resolution      = 1920x1080
```

### Simulation & Detection

```python
SIMULATION_MODE          = False   # True = Run without hardware
PAPER_DETECTION_ENABLED  = False   # True = Capture photo after paper detected
```

---

## Vision Module

| Module | File | Function |
|------|------|------|
| OCR | `vision/ocr.py` | PaddleOCR Chinese field extraction + position detection |
| QR Code | `vision/qr_scanner.py` | pyzbar scanning → Document type identification |
| Classification | `vision/classifier.py` | Keyword + regex + field hit scoring classification |
| Comparison | `vision/comparator.py` | SSIM image similarity + OCR field comparison |
| Page Count | `vision/page_counter.py` | Multi-page document completeness check |
| Camera | `vision/camera.py` | Shared camera singleton + frame buffer |
| Example Generation | `vision/example_generator.py` | PIL rendered template example images |

### OCR Environment Variables

```python
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = 'True'
FLAGS_use_mkldnn = '0'       # Disable MKL-DNN
CUDA_VISIBLE_DEVICES = '-1'  # CPU mode
```

---

## Web Security Configuration

```python
SECRET_KEY    = 'stamp_robot_mec202_secret'
WEB_HOST      = '0.0.0.0'
WEB_PORT      = 5001
```

---

## DMS Integration (Optional)

```python
DMS_BASE_URL = ''    # Document Management System API address
DMS_API_KEY  = ''    # API key
```

---

## Document Processing Core Workflow

```
Capture photo → Paper detection → QR code scanning → OCR field extraction
→ Auto classification → Template field extraction → Multi-page detection → Rule validation
→ Stamp positioning (IK/calibration/template/default) → Stamping → Archive photo → Audit log
```
