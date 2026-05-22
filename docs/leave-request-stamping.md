# Leave Request Verification Auto-Stamping Robot

> **Course Project MEC202 · SPECIFIC GENERAL PROJECT 9**
> Leave Request Verification and Auto-Stamping Robot
> A robot server for self service of documentation
> Instructor: Bangxiang Chen (Bangxiang.chen@xjtlu.edu.cn)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Business Scenarios](#2-core-business-scenarios)
3. [System Architecture](#3-system-architecture)
4. [Complete Business Workflow](#4-complete-business-workflow)
5. [Verification Logic and Decision Mechanism](#5-verification-logic-and-decision-mechanism)
6. [Feature List](#6-feature-list)
7. [Database Design](#7-database-design)
8. [Backend API Design](#8-backend-api-design)
9. [Frontend Page Design](#9-frontend-page-design)
10. [Leave Request Template and OCR Field Extraction](#10-leave-request-template-and-ocr-field-extraction)
11. [Robotic Arm Stamping and Safety Control](#11-robotic-arm-stamping-and-safety-control)
12. [Superpower Phased Development Plan](#12-superpower-phased-development-plan)
13. [Final Acceptance Criteria](#13-final-acceptance-criteria)
14. [Software Environment and Installation](#14-software-environment-and-installation)
15. [Quick Start](#15-quick-start)
16. [Production Run: Connecting Hardware](#16-production-run-connecting-hardware)
17. [Project File Structure](#17-project-file-structure)
18. [Team Division of Work](#18-team-division-of-work)
19. [Development Timeline](#19-development-timeline)
20. [Hardware Assembly Guide](#20-hardware-assembly-guide)
21. [Configuration](#21-configuration)
22. [FAQ](#22-faq)
23. [Procurement List](#23-procurement-list)
24. [Modification Task Instructions for Claude Code](#24-modification-task-instructions-for-claude-code)

---

## 1. Project Overview

This project is a **leave request verification auto-stamping robot system** designed for school administrative scenarios.

The system adopts a workflow of "online application + QR code binding + offline scan verification + auto-stamping + audit trail": students first submit leave requests on the web portal; after approval by administrators or teachers, the system generates a unique application ID and a tamper-proof QR code. Students bring the paper leave request with the QR code to the offline device, where the robot scans the QR code via camera and uses OCR to recognize the paper content, then compares the paper content with the online application record. Only after successful verification does the robotic arm perform the auto-stamping.

This project does not merely judge "whether this paper looks like a leave request." Instead, it determines:

> Whether this paper leave request corresponds to a genuinely existing, already approved, not-yet-stamped online leave application with matching content in the system.

**Core Value:**

- Prevent forged leave requests from being stamped.
- Prevent unapproved applications from being stamped offline.
- Prevent duplicate stamping of the same application.
- Reduce the burden of manual review and hand stamping.
- Achieve full-process traceability through OCR results, verification results, before/after stamping images, and operation logs.

---

## 2. Core Business Scenarios

### 2.1 User Roles

| Role | Permissions |
|---|---|
| Student | Submit leave requests online, view application status, download or print leave requests with QR codes |
| Operator | Scan leave requests at the offline device, trigger verification and stamping workflow |
| Reviewer | Handle REVIEW tasks that the system cannot automatically determine |
| Admin | Manage users, templates, applications, approvals, reviews, logs, and system configuration |

### 2.2 Leave Application Status

| Status | Meaning |
|---|---|
| `SUBMITTED` | Student has submitted, awaiting approval |
| `APPROVED` | Approved, awaiting offline stamping |
| `REJECTED` | Approval rejected |
| `STAMPED` | Stamping completed |
| `CANCELLED` | Cancelled |
| `EXPIRED` | Expired |

### 2.3 Stamping Task Status

| Status | Meaning |
|---|---|
| `CREATED` | Task created |
| `CAPTURING` | Capturing paper document image |
| `QR_SCANNING` | Scanning QR code |
| `OCR_RUNNING` | Running OCR |
| `VERIFYING` | Running rule verification |
| `PASS` | Auto-verification passed |
| `REVIEW` | Entered manual review |
| `REJECT` | Auto-rejected |
| `STAMPING` | Robotic arm stamping in progress |
| `STAMPED` | Successfully stamped |
| `STAMP_FAILED` | Stamping failed |
| `ARCHIVED` | Archived |

---

## 3. System Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                       Frontend React SPA                       │
│  Login / Leave Application / Operator Console / Manual Review  │
│  Audit Log / Templates / Calibration                           │
│  React 19 + Vite + TypeScript + TailwindCSS + Zustand          │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTP API / MJPEG Stream
┌─────────────────────────────▼────────────────────────────────┐
│                         FastAPI Backend                        │
│  Auth · Leave Application · Stamping Task · OCR · Verification │
│  Review · Logs · Calibration                                   │
└───────┬──────────────┬─────────────┬─────────────┬────────────┘
        │              │             │             │
        ▼              ▼             ▼             ▼
   api/leave       vision/        validator/     hardware/
   Leave API       Camera/OCR     Leave Validator  Arm Control
   Stamp API       QR Scanning    Risk Scoring    Calibration & Stamping
        │              │             │             │
        └──────────────┴─────────────┴─────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                           MySQL                                │
│ users / personnel / leave_applications / stamp_tasks           │
│ verification_results / doc_templates / template_fields         │
│ audit_log / review_queue                                      │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite + TypeScript + TailwindCSS v4 |
| State Management | Zustand |
| Routing | React Router |
| Charts | Recharts |
| Backend | Python 3.11+ + FastAPI |
| Database | MySQL 8.0 + SQLAlchemy + Alembic |
| OCR | PaddleOCR / PaddlePaddle |
| Image Processing | OpenCV / Pillow / scikit-image |
| QR Code | pyzbar |
| Robotic Arm | WeArm Serial / Hiwonder ArmPi WiFi |
| Monorepo | Turborepo + pnpm workspaces |

---

## 4. Complete Business Workflow

```text
① Student logs into the system and submits a leave request online
        │
② System generates application_id, e.g., LEAVE-20260511-0001
        │
③ Admin or reviewer approves the application
        │
④ After approval, the application status changes to APPROVED
        │
⑤ System generates a QR code payload with HMAC signature
        │
⑥ Student prints or brings the paper leave request with the QR code
        │
⑦ Operator logs into the offline stamping robot system
        │
⑧ Place the paper leave request into the A4 alignment slot
        │
⑨ Click "Scan Leave Request and Verify for Stamping"
        │
⑩ Camera captures the before image
        │
⑪ System scans the QR code and verifies the signature
        │
⑫ Query LeaveApplication using application_id
        │
⑬ Check if the application exists, is APPROVED, and has not been stamped
        │
⑭ PaddleOCR recognizes the full text of the paper leave request
        │
⑮ Extract name, student ID, leave type, dates, reason, etc. based on leave template
        │
⑯ Compare OCR fields with the online application record
        │
⑰ Generate risk score and decision: PASS / REVIEW / REJECT
        │
├── PASS   → Capture another photo before stamping to confirm paper hasn't moved → Robotic arm stamps → after image → Audit log
├── REVIEW → Enter manual review queue → Reviewer decides whether to stamp
└── REJECT → Reject stamping → Display specific reason → Audit log
```

---

## 5. Verification Logic and Decision Mechanism

The system uses multi-layer verification and does not rely on a single OCR result.

### 5.1 Verification Items

| Verification Item | Rule | Failure Handling |
|---|---|---|
| QR Code Signature Verification | Use HMAC-SHA256 to verify whether the QR code payload has been tampered with | Reject on failure |
| Application Record Verification | application_id must exist in `leave_applications` | Reject if not found |
| Application Status Verification | Status must be `APPROVED` | Reject if unapproved, rejected, or already stamped |
| Duplicate Stamp Verification | `stamped_at` must be empty | Reject if already stamped |
| Student ID Consistency Verification | OCR student ID must match the application record exactly | Reject if inconsistent |
| Name Consistency Verification | Minor differences such as spaces and case are allowed | Minor inconsistency → REVIEW; obvious inconsistency → REJECT |
| Leave Type Verification | OCR leave type should match the application record | Missing → REVIEW; obvious inconsistency → REJECT |
| Date Consistency Verification | Start date and end date must match; end date cannot be earlier than start date | Missing → REVIEW; inconsistent → REJECT |
| Reason Field Verification | Reason should not be empty | Empty → REVIEW |
| OCR Confidence Verification | >=0.85 PASS, 0.65-0.85 REVIEW, <0.65 REJECT | Processed by threshold |
| Template Matching Verification | Document should match the leave template | No match → REJECT; low confidence → REVIEW |
| Paper Position Verification | Capture another photo before stamping to check if paper has moved | Obvious movement → REVIEW |

### 5.2 Decision Results

| Decision | Meaning | Action |
|---|---|---|
| `PASS` | Low risk, all critical verifications passed | Auto-stamp |
| `REVIEW` | Medium risk, some fields uncertain | Enter manual review |
| `REJECT` | High risk or hard rule failure | Reject stamping |

### 5.3 Risk Score Calculation

Suggested rules:

| Type | Score |
|---|---|
| Critical failure | +70 |
| General failure | +40 |
| Warning | +10 to +25 |
| Maximum score | 100 |

Final determination:

```text
Hard fail exists     → REJECT
risk_score >= 70    → REJECT
risk_score >= 40    → REVIEW
risk_score < 40     → PASS
```

### 5.4 Verification Result Example

```json
{
  "decision": "PASS",
  "risk_score": 8,
  "checks": [
    {
      "name": "qr_signature_check",
      "result": "pass",
      "score": 0,
      "reason": "QR code signature verification passed"
    },
    {
      "name": "student_id_match_check",
      "result": "pass",
      "score": 0,
      "reason": "Student ID matches the application record"
    },
    {
      "name": "ocr_confidence_check",
      "result": "pass",
      "score": 8,
      "reason": "OCR confidence meets the auto-pass threshold"
    }
  ],
  "errors": [],
  "warnings": []
}
```

---

## 6. Feature List

| Feature | Priority | Implementation | Status |
|---|---:|---|---|
| User Login/Registration | P0 | FastAPI auth + React page | Existing |
| Leave Application Creation | P0 | `/api/leave-applications` | New |
| Leave Application Approval/Rejection | P0 | admin/reviewer permissions | New |
| QR Code Payload Generation | P0 | HMAC-SHA256 signing | New |
| QR Code Scanning | P0 | pyzbar + OpenCV | Existing, needs integration with leave workflow |
| OCR Recognition | P0 | PaddleOCR | Existing, needs integration with leave_extractor |
| Leave Request Field Extraction | P0 | Template regex + default regex | New |
| Leave Request Rule Verification | P0 | `validator/leave_validator.py` | New |
| Risk Scoring | P0 | PASS / REVIEW / REJECT | New |
| Auto-Stamping | P0 | Existing hardware module | Existing, needs integration with new workflow |
| Manual Review | P0 | review_queue + ReviewPage | Existing, needs enhancement |
| Audit Log | P0 | audit_log + before/after images | Existing, needs enhancement |
| Duplicate Stamp Detection | P0 | `stamped_at` and task status | New |
| Paper Movement Detection | P1 | comparator / SSIM | Optional enhancement |
| Post-Stamp Quality Detection | P1 | After image + red area detection | Optional enhancement |
| DMS Integration | P2 | REST API | Optional |

---

## 7. Database Design

### 7.1 `leave_applications` Table

```sql
CREATE TABLE leave_applications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  application_id VARCHAR(64) UNIQUE NOT NULL,
  student_id VARCHAR(20) NOT NULL,
  student_name VARCHAR(50) NOT NULL,
  dept VARCHAR(100),
  leave_type VARCHAR(50) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  reason TEXT NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
  qr_content TEXT,
  approved_by VARCHAR(50),
  approved_at VARCHAR(30),
  stamped_at VARCHAR(30),
  created_at VARCHAR(30),
  updated_at VARCHAR(30)
);
```

### 7.2 `stamp_tasks` Table

```sql
CREATE TABLE stamp_tasks (
  id INT PRIMARY KEY AUTO_INCREMENT,
  task_id VARCHAR(64) UNIQUE NOT NULL,
  application_id VARCHAR(64),
  operator_id VARCHAR(50),
  doc_type VARCHAR(50) DEFAULT 'leave',
  status VARCHAR(30),
  decision VARCHAR(30),
  risk_score INT DEFAULT 0,
  before_img VARCHAR(500),
  after_img VARCHAR(500),
  qr_content TEXT,
  extracted_fields TEXT,
  verification_result TEXT,
  error_message TEXT,
  created_at VARCHAR(30),
  updated_at VARCHAR(30)
);
```

### 7.3 `verification_results` Table

```sql
CREATE TABLE verification_results (
  id INT PRIMARY KEY AUTO_INCREMENT,
  task_id VARCHAR(64) NOT NULL,
  check_name VARCHAR(100) NOT NULL,
  result VARCHAR(30) NOT NULL,
  score INT DEFAULT 0,
  reason TEXT,
  created_at VARCHAR(30)
);
```

### 7.4 Extended `audit_log`

Suggested new fields:

```sql
ALTER TABLE audit_log ADD COLUMN application_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN task_id VARCHAR(64);
ALTER TABLE audit_log ADD COLUMN decision VARCHAR(30);
ALTER TABLE audit_log ADD COLUMN risk_score INT DEFAULT 0;
ALTER TABLE audit_log ADD COLUMN verification_result TEXT;
```

### 7.5 Extended `review_queue`

Suggested new fields:

```sql
ALTER TABLE review_queue ADD COLUMN application_id VARCHAR(64);
ALTER TABLE review_queue ADD COLUMN task_id VARCHAR(64);
ALTER TABLE review_queue ADD COLUMN risk_score INT DEFAULT 0;
ALTER TABLE review_queue ADD COLUMN verification_result TEXT;
```

---

## 8. Backend API Design

### 8.1 Leave Application API

Unified prefix:

```text
/api/leave-applications
```

| Method | Path | Description |
|---|---|---|
| POST | `/api/leave-applications` | Create a leave application |
| GET | `/api/leave-applications` | Get application list, supports status filtering |
| GET | `/api/leave-applications/{application_id}` | Get application details |
| POST | `/api/leave-applications/{application_id}/approve` | Approve the application |
| POST | `/api/leave-applications/{application_id}/reject` | Reject the application |
| GET | `/api/leave-applications/{application_id}/qr` | Get QR code payload or QR code image |

#### Create Leave Application Request Example

```json
{
  "student_id": "20230001",
  "student_name": "Zhang San",
  "dept": "School of Smart Engineering",
  "leave_type": "Sick Leave",
  "start_date": "2026-05-11",
  "end_date": "2026-05-12",
  "reason": "Feeling unwell, need to rest"
}
```

### 8.2 Stamping Task API

| Method | Path | Description |
|---|---|---|
| POST | `/api/stamp/leave` | Scan leave request and verify for stamping |
| GET | `/api/stamp-tasks/{task_id}` | Get stamping task details |
| POST | `/api/stamp-tasks/{task_id}/retry` | Optional: retry failed task |

`POST /api/stamp/leave` workflow:

```text
Create StampTask
→ Capture before image
→ Scan QR code
→ Verify QR code signature
→ Query LeaveApplication
→ OCR
→ Extract leave request fields
→ Rule verification
→ Save VerificationResult
→ PASS/REVIEW/REJECT
→ Stamp or review or reject
→ Write to audit_log
```

### 8.3 Manual Review API

Uses the existing review module with enhanced field display.

| Method | Path | Description |
|---|---|---|
| GET | `/api/review/pending` | Pending review task list |
| POST | `/api/review/{id}/resolve` | Process review task |

When review is approved:

```text
Confirm application is still APPROVED
Confirm stamped_at is empty
Call stamping logic
Update review_queue
Update stamp_tasks
Update leave_applications
Write to audit_log
```

When review is rejected:

```text
Update review_queue
Update stamp_tasks
Do not call robotic arm
Write to audit_log
```

---

## 9. Frontend Page Design

### 9.1 New Routes

| Path | Page | Permission |
|---|---|---|
| `/applications` | Leave application list | Authenticated users |
| `/applications/new` | New leave application | Authenticated users |
| `/applications/:applicationId` | Leave application details | Authenticated users |

### 9.2 Leave Application List Page

File:

```text
apps/web/src/pages/LeaveApplicationsPage.tsx
```

Features:

- Display application list.
- Filter by status.
- Display application_id, name, student ID, department, leave type, start date, end date, status.
- admin/reviewer can approve or reject.
- Click to enter detail page.

### 9.3 New Leave Application Page

File:

```text
apps/web/src/pages/NewLeaveApplicationPage.tsx
```

Fields:

- Student ID `student_id`
- Name `student_name`
- Department `dept`
- Leave Type `leave_type`
- Start Date `start_date`
- End Date `end_date`
- Reason `reason`

After successful submission, redirect to the application detail page.

### 9.4 Leave Application Detail Page

File:

```text
apps/web/src/pages/LeaveApplicationDetailPage.tsx
```

Display:

- Application details.
- Current status.
- QR code payload or QR code image.
- Approval information.
- Stamping time.

### 9.5 Operator Console Page

Main button changed to:

```text
Scan Leave Request and Verify for Stamping
```

Calls:

```text
POST /api/stamp/leave
```

Displays:

- application_id
- task_id
- student_id
- student_name
- leave_type
- start_date
- end_date
- decision
- risk_score
- checks
- errors
- warnings
- before_img
- after_img
- Final status

### 9.6 Review Page

Enhance existing ReviewPage to display:

- task_id
- application_id
- risk_score
- extracted_fields
- verification_result
- warnings
- before image
- approve / reject actions

### 9.7 Logs Page

Enhance existing LogsPage to add display of:

- application_id
- task_id
- decision
- risk_score
- verification_result

When old logs lack these fields, the page must not crash.

---

## 10. Leave Request Template and OCR Field Extraction

### 10.1 Leave Template Configuration

Ensure the following exists in `doc_templates`:

```json
{
  "code": "leave",
  "name": "Leave Request",
  "requires_stamp": 1,
  "stamp_position": "420,650",
  "classification_keywords": [
    "Leave Request",
    "Leave Application",
    "请假条",
    "请假申请"
  ],
  "stamp_keywords": [
    "Approval Comments",
    "School Stamp",
    "Stamp",
    "Approved"
  ]
}
```

### 10.2 template_fields

Ensure the leave template contains the following fields:

| Field Name | Label | Required | Example |
|---|---|---|---|
| application_id | Application ID | Yes | LEAVE-20260511-0001 |
| student_name | Name | Yes | Zhang San |
| student_id | Student ID | Yes | 20230001 |
| dept | Department | Optional | School of Smart Engineering |
| leave_type | Leave Type | Yes | Sick Leave |
| start_date | Start Date | Yes | 2026-05-11 |
| end_date | End Date | Yes | 2026-05-12 |
| reason | Reason | Yes | Feeling unwell |

### 10.3 Field Extraction Module

New file:

```text
apps/backend/vision/leave_extractor.py
```

Core function:

```python
extract_leave_fields(ocr_text: str, template_fields: list | None = None) -> dict
```

Extracted fields:

```text
application_id
student_name
student_id
dept
leave_type
start_date
end_date
reason
```

Extraction strategy:

```text
Prioritize template_fields.ocr_pattern
Fall back to default regex on failure
Normalize dates to YYYY-MM-DD format
Return None or empty string for missing fields; do not throw fatal exceptions
```

---

## 11. Robotic Arm Stamping and Safety Control

### 11.1 Stamping Coordinates

Prioritize template configuration:

```text
stamp_position = "420,650"
```

If stamp_keywords exist, keyword-based positioning can be used in combination.

Recommended order:

```text
Fixed template coordinates → Near-keyword positioning → Default safe coordinates → Manual review
```

### 11.2 Paper Position Confirmation Before Stamping

Do not stamp immediately after PASS. Capture another photo:

```text
Verification passed
→ Capture photo again before stamping
→ Check if paper position has shifted significantly
→ Only execute robotic arm stamping if no shift
→ If shifted, enter REVIEW
```

### 11.3 Post-Stamp Photo Capture

Capture an after image after stamping for:

- Audit trail.
- Determining whether the robotic arm has completed execution.
- Future extension to stamp success detection.

### 11.4 Simulation Mode

Prioritize during development and testing:

```python
SIMULATION_MODE = True
```

In simulation mode:

- Does not connect to a real robotic arm.
- Returns simulated stamp success on PASS.
- Still writes to StampTask, VerificationResult, and audit_log.

---

## 12. Superpower Phased Development Plan

Development requirements:

1. Do not perform large-scale refactoring all at once.
2. Complete only one small, verifiable feature point at a time.
3. After completing each feature point, immediately run a quick test.
4. After the test passes, proceed to the next feature point.
5. If the test fails, fix the current feature first before moving forward.
6. Reuse existing code as much as possible; do not rewrite from scratch.
7. After each modification step, output:
   - Which files were modified.
   - What new interfaces or functions were added.
   - How to quickly test.
   - Whether the test result passed.
   - The next step plan.

### Phase 1: Database Models and Migration

Goal: Add data structures for leave applications, stamping tasks, and verification results.

To complete:

- Add `LeaveApplication`.
- Add `StampTask`.
- Add `VerificationResult`.
- Create Alembic migration or use the project's existing initialization logic.
- Ensure no impact on existing `users`, `personnel`, `doc_templates`, `template_fields`, `audit_log`, `review_queue`.

Quick test:

```text
1. Run database migration.
2. Check MySQL for:
   - leave_applications
   - stamp_tasks
   - verification_results
3. Start the backend.
4. Open http://127.0.0.1:5001/docs.
5. Confirm the service has no errors.
```

Pass criteria:

- Backend starts normally.
- New tables created successfully.
- Existing login API has no errors.
- Existing template management API has no errors.

### Phase 2: QR Code Signing Tool

Goal: Implement QR code content generation and tamper-proof verification.

New file:

```text
apps/backend/utils/qr_sign.py
```

Quick test:

```python
from utils.qr_sign import create_leave_qr_payload, verify_qr_payload

payload = create_leave_qr_payload("LEAVE-20260511-0001", "20230001")
assert verify_qr_payload(payload) is True

payload["student_id"] = "99999999"
assert verify_qr_payload(payload) is False

print("QR sign test passed")
```

Pass criteria:

- Normal payload verification passes.
- Tampered student_id verification fails.
- Backend startup is not affected.

### Phase 3: Leave Application API

Goal: Implement creation, querying, approval, rejection, and QR code viewing.

Quick test:

```bash
curl -X POST http://127.0.0.1:5001/api/leave-applications \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "20230001",
    "student_name": "Zhang San",
    "dept": "School of Smart Engineering",
    "leave_type": "Sick Leave",
    "start_date": "2026-05-11",
    "end_date": "2026-05-12",
    "reason": "Feeling unwell, need to rest"
  }'
```

```bash
curl http://127.0.0.1:5001/api/leave-applications
curl -X POST http://127.0.0.1:5001/api/leave-applications/LEAVE-20260511-0001/approve
curl http://127.0.0.1:5001/api/leave-applications/LEAVE-20260511-0001/qr
```

Pass criteria:

- Can create leave application.
- application_id is auto-generated.
- qr_content is auto-generated.
- Can query applications.
- Can approve.
- After approval, status = APPROVED.

### Phase 4: Leave Request OCR Field Extraction

Quick test:

```python
from vision.leave_extractor import extract_leave_fields

text = '''
Leave Request
Application ID: LEAVE-20260511-0001
Name: Zhang San
Student ID: 20230001
Department: School of Smart Engineering
Leave Type: Sick Leave
Start Date: 2026-05-11
End Date: 2026-05-12
Reason: Feeling unwell, need to rest
'''

fields = extract_leave_fields(text)
assert fields["application_id"] == "LEAVE-20260511-0001"
assert fields["student_name"] == "Zhang San"
assert fields["student_id"] == "20230001"
assert fields["leave_type"] == "Sick Leave"
assert fields["start_date"] == "2026-05-11"
assert fields["end_date"] == "2026-05-12"
assert "unwell" in fields["reason"]

print("Leave extractor test passed")
```

Pass criteria:

- Chinese leave request fields can be correctly extracted.
- English leave request fields can be correctly extracted.
- Date format normalized to YYYY-MM-DD.
- No crash when fields are missing.

### Phase 5: Leave Request Validator

Goal: Implement PASS / REVIEW / REJECT decision logic.

Test scenarios:

| Scenario | Expected |
|---|---|
| Normal application + matching fields + high OCR confidence | PASS |
| Unapproved application | REJECT |
| Student ID mismatch | REJECT |
| Medium OCR confidence | REVIEW |
| Already stamped application scanned again | REJECT |
| QR code tampered | REJECT |

Pass criteria:

- Every result has checks and reason.
- No uncaught exceptions.
- Hard fails never result in auto-stamping.

### Phase 6: Leave Request Stamping API

Endpoint:

```text
POST /api/stamp/leave
```

Quick test:

```bash
curl -X POST http://127.0.0.1:5001/api/stamp/leave
```

Pass criteria:

- Returns success.
- Returns task_id.
- Returns decision.
- Returns checks.
- In SIMULATION_MODE, does not connect to robotic arm and does not crash.
- `stamp_tasks` has a record.
- `verification_results` has a record.
- `audit_log` has a record.

### Phase 7: Manual Review Workflow

Quick test:

```bash
curl http://127.0.0.1:5001/api/review/pending
```

Pass criteria:

- REVIEW tasks can be processed.
- Approval triggers stamping or simulated stamping.
- Rejection does not trigger stamping.
- Data state is consistent.

### Phase 8: Frontend Leave Application Pages

Quick test:

```bash
pnpm dev
```

Open:

```text
http://localhost:5173/applications
```

Pass criteria:

- Page does not show white screen.
- Form can be submitted.
- List can be refreshed.
- Details can be opened.
- Approval buttons work.
- Backend data state changes correctly.

### Phase 9: Frontend Operator Console Integration

Pass criteria:

- PASS displays "Verification passed, auto-stamped."
- REVIEW displays "Verification uncertain, entered manual review."
- REJECT displays "Verification failed, stamping rejected."
- Checks are displayed item by item.
- Error messages are clear.
- Page does not crash.

### Phase 10: Review Page and Logs Page Enhancement

Pass criteria:

- Review page can process tasks.
- Logs page displays new fields.
- Old logs do not cause page errors.
- Image paths display correctly or show fallback messages.

---

## 13. Final Acceptance Criteria

### Acceptance 1: Normal Pass Workflow

Steps:

1. Admin logs in.
2. Create a leave application:
   - student_id = 20230001
   - student_name = Zhang San
   - leave_type = Sick Leave
   - start_date = 2026-05-11
   - end_date = 2026-05-12
   - reason = Feeling unwell
3. Admin approves.
4. Detail page displays QR code payload.
5. Place the QR code on the leave request.
6. Operator console clicks "Scan Leave Request and Verify for Stamping."
7. System completes QR code verification, OCR, field comparison, risk scoring.
8. Returns decision = PASS.
9. Robotic arm executes stamping, or simulation mode displays stamped.
10. LeaveApplication status changes to STAMPED.
11. audit_log has a complete record.
12. before_img and after_img have paths.

Pass criteria:

- Entire workflow has no errors.
- Database state is correct.
- Page display is clear.
- Audit log is complete.

### Acceptance 2: Unapproved Application Rejection Workflow

Steps:

1. Create a leave application but do not approve it.
2. Scan the leave request.
3. System returns REJECT.
4. Reason includes "application not yet approved."
5. Robotic arm is not called.
6. audit_log has a rejection record.

Pass criteria:

> Unapproved applications will never be stamped.

### Acceptance 3: Student ID Mismatch Rejection Workflow

Steps:

1. Create and approve an application.
2. Change the student ID on the paper leave request to a different one.
3. Scan.
4. System returns REJECT.
5. Reason includes "student ID mismatch."
6. Robotic arm is not called.

Pass criteria:

> Student ID mismatches will never be stamped.

### Acceptance 4: Unclear OCR Review Workflow

Steps:

1. Prepare a leave request with low OCR confidence or missing fields.
2. Scan.
3. System returns REVIEW.
4. review_queue shows the task.
5. Review page can display the task.
6. Reviewer can approve or reject.

Pass criteria:

> Uncertain situations will not be auto-stamped; they must enter manual review.

### Acceptance 5: Duplicate Stamping Rejection Workflow

Steps:

1. First stamping of the same application succeeds.
2. Scan the same QR code again.
3. System returns REJECT.
4. Reason includes "this application has already been stamped."
5. Robotic arm is not called.

Pass criteria:

> The same application cannot be stamped twice.

### Acceptance 6: QR Code Tampering Rejection Workflow

Steps:

1. Modify the student_id or application_id in the QR code payload.
2. Keep sig unchanged.
3. Scan.
4. System returns REJECT.
5. Reason includes "QR code signature invalid" or "QR code verification failed."

Pass criteria:

> Tampered QR codes cannot pass verification.

### Acceptance 7: System Compatibility Acceptance

Confirm old features still work:

- Login
- Registration
- User management
- Template management
- Camera preview
- Robotic arm calibration
- Manual review
- Audit log
- Existing general stamping API

Pass criteria:

- Old pages do not show white screen.
- Old APIs do not return 500.
- New features do not break the original system.

---

## 14. Software Environment and Installation

### Environment Requirements

- Python 3.11+
- Node.js 18+
- pnpm
- MySQL 8.0
- Memory 4GB+, PaddleOCR model loading requires approximately 1.5GB

### Install Dependencies

```bash
# After cloning the project, enter the root directory
cd MEC202

# Install pnpm
npm install -g pnpm

# Install frontend and monorepo dependencies
pnpm install

# Install backend dependencies
cd apps/backend
pip install -r requirements.txt
# Or use uv
uv sync
```

### Database Initialization

```bash
cd apps/backend
alembic upgrade head
```

If the project does not use Alembic, use the existing initialization script to create database tables.

---

## 15. Quick Start

### Turborepo Start

```bash
pnpm dev
```

### Manual Start

```bash
# Terminal 1: Start backend
cd apps/backend
python -m api.main

# Terminal 2: Start frontend
cd apps/web
pnpm dev
```

### Access URLs

| Mode | URL |
|---|---|
| Frontend Development | http://localhost:5173 |
| Backend API | http://127.0.0.1:5001 |
| Swagger | http://127.0.0.1:5001/docs |
| ReDoc | http://127.0.0.1:5001/redoc |

### Demo Accounts

| Account | Password | Role |
|---|---|---|
| admin | admin123 | Admin |
| operator1 | op123 | Operator |
| reviewer1 | reviewer123 | Reviewer |

---

## 16. Production Run: Connecting Hardware

1. Connect USB camera.
2. Connect WeArm robotic arm or Hiwonder ArmPi.
3. Confirm MySQL is running normally.
4. Set `SIMULATION_MODE = False`.
5. Start the service:

```bash
pnpm dev
```

6. Open browser and log into the system.
7. Enter the robotic arm calibration page and complete four-corner calibration.
8. Enter the operator console and execute "Scan Leave Request and Verify for Stamping."

---

## 17. Project File Structure

```text
MEC202/
├── turbo.json
├── pnpm-workspace.yaml
├── package.json
│
├── apps/
│   ├── backend/
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── auth.py
│   │   │   ├── leave_applications.py   # New: Leave Application API
│   │   │   ├── stamp.py                # Modified: integrate /api/stamp/leave
│   │   │   ├── review.py               # Modified: integrate leave task
│   │   │   ├── cameras.py
│   │   │   ├── logs.py
│   │   │   ├── templates.py
│   │   │   ├── calibration.py
│   │   │   └── users.py
│   │   │
│   │   ├── database/
│   │   │   ├── models.py               # New: LeaveApplication / StampTask / VerificationResult
│   │   │   └── connection.py
│   │   │
│   │   ├── vision/
│   │   │   ├── ocr.py
│   │   │   ├── qr_scanner.py
│   │   │   ├── classifier.py
│   │   │   ├── comparator.py
│   │   │   └── leave_extractor.py      # New: Leave request field extraction
│   │   │
│   │   ├── validator/
│   │   │   └── leave_validator.py      # New: Leave request validator
│   │   │
│   │   ├── hardware/
│   │   └── utils/
│   │       └── qr_sign.py              # New: QR code signing tool
│   │
│   └── web/
│       └── src/
│           ├── App.tsx                 # Modified: new routes added
│           ├── pages/
│           │   ├── LeaveApplicationsPage.tsx
│           │   ├── NewLeaveApplicationPage.tsx
│           │   ├── LeaveApplicationDetailPage.tsx
│           │   ├── ReviewPage.tsx
│           │   └── LogsPage.tsx
│           ├── lib/
│           │   └── api.ts
│           └── types/
│               └── index.ts
```

---

## 18. Team Division of Work

| Member | Module | Core Files | Deliverable |
|---|---|---|---|
| A: Hardware | Robotic arm, calibration, stamping path | `apps/backend/hardware/` | Robotic arm can stamp stably; simulation/real mode switchable |
| B: Vision | OCR, QR code, field extraction | `vision/ocr.py`, `vision/qr_scanner.py`, `vision/leave_extractor.py` | Leave request field extraction accurate, QR code recognition stable |
| C: Verification Logic | Leave request validator, risk scoring | `validator/leave_validator.py` | PASS/REVIEW/REJECT logic clear and reliable |
| D: Frontend | Leave application, operator console, review, logs | `apps/web/src/pages/` | Pages complete, result display clear |
| E: Integration | API, database, end-to-end workflow | `api/leave_applications.py`, `api/stamp.py`, `database/models.py` | Full end-to-end workflow passes |

---

## 19. Development Timeline

```text
Week 1: Database models, QR code signing, leave application API
Week 2: OCR field extraction, leave request validator, template field configuration
Week 3: /api/stamp/leave full workflow, simulation mode testing
Week 4: Frontend leave application pages, operator console integration, review page enhancement
Week 5: Hardware integration, robotic arm stamping, paper position confirmation
Week 6: Exception scenario testing, acceptance demo, report and video recording
```

---

## 20. Hardware Assembly Guide

### Frame Construction

1. Use KT board to build an A4 alignment slot.
2. Fix the camera at the top center, facing the document area directly.
3. Fix the robotic arm on the side, with a stamp attached to the end effector.
4. Mark the A4 placement area on the base board.
5. Ensure the paper is stable after placement and does not shift easily.

### Calibration

1. Open the `/calibration` page.
2. Test the robotic arm connection.
3. Adjust servos to four-corner positions.
4. Save TL/TR/BL/BR four-corner calibration points.
5. Test whether the stamping point is accurate.

---

## 21. Configuration

Key configuration in `apps/backend/config.py`:

```python
# Robotic arm type
ARM_TYPE = 'wearm'  # 'wearm' or 'hiwonder'

# Simulation mode
SIMULATION_MODE = True  # Recommended True during development, change to False when connecting hardware

# Database configuration
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'stamp_robot'
DB_PASSWORD = 'stamp_robot_pwd'
DB_NAME = 'stamp_robot'

# Web security
SECRET_KEY = 'stamp_robot_mec202_secret'

# Camera and paper detection
PAPER_DETECTION_ENABLED = False
```

---

## 22. FAQ

### Q1: Why can't we rely solely on template matching?

Because templates can only determine "whether the format looks right" but cannot prove "whether this document has actually gone through online approval." This system binds the online application record through application_id and QR code signature, then uses OCR to compare with the database, thereby determining whether the paper leave request is genuine and valid.

### Q2: What if a student modifies the QR code?

The QR code payload uses HMAC-SHA256 signing. As long as the application_id or student_id is modified, the signature verification will fail, and the system will reject the stamping.

### Q3: What if OCR recognition is unclear?

When OCR confidence is low or fields are missing, the system does not auto-stamp but instead enters manual review.

### Q4: Can the same application be stamped twice?

No. After the first successful stamping, `LeaveApplication.status` changes to `STAMPED` and `stamped_at` is not empty. Scanning the same QR code again will be rejected.

### Q5: Can development proceed without a robotic arm?

Yes. Set:

```python
SIMULATION_MODE = True
```

The system will simulate stamping success but still write to tasks, verification results, and audit logs.

---

## 23. Procurement List

| # | Taobao Search Term | Specifications | Estimated Price |
|---|---|---|---:|
| 1 | Arduino Uno R3 board official compatible | Includes USB cable | ~40 CNY |
| 2 | MG996R servo metal gear | 1 piece | ~25 CNY |
| 3 | MG90S micro servo | 1 piece | ~15 CNY |
| 4 | 1080P USB camera driverless wide-angle | Plug and play | ~60 CNY |
| 5 | Self-inking stamp custom engraving | Engrave "Approved" or similar | ~25 CNY |
| 6 | KT board A3 white 5mm | 3-5 sheets | ~15 CNY |
| 7 | Hot glue gun set | Includes glue sticks | ~20 CNY |
| 8 | Dupont wires male-to-female 20cm 40 pcs | 1 pack | ~8 CNY |
| | | **Total** | **~208 CNY** |

---

## 24. Modification Task Instructions for Claude Code

Please follow these requirements for code modifications:

```text
You are modifying the MEC202 document stamping robot project.

Please read the entire project structure first. Do not rewrite the project or overturn existing code. Make incremental modifications based on the existing FastAPI, React, MySQL, OCR, QR code, robotic arm, audit log, and manual review modules.

Modification Goal:
Transform the current general document recognition and stamping system into a complete closed-loop system of "online leave application + offline leave request verification + auto-stamping."

Core Business:
Students first submit leave requests online. The system creates application records and generates QR codes. After admin approval, students bring the paper leave request with QR code to the offline robot. The system scans the QR code, queries the application record using application_id, recognizes paper content via OCR, and compares it with the online application record. Only when the application genuinely exists, has been approved, has not been stamped before, and the paper content matches, does the system allow auto-stamping.

Must Add:
1. LeaveApplication model and leave_applications table.
2. StampTask model and stamp_tasks table.
3. VerificationResult model and verification_results table.
4. utils/qr_sign.py, implementing HMAC-SHA256 QR code signing and verification.
5. api/leave_applications.py, implementing leave application creation, querying, approval, rejection, and QR code viewing.
6. vision/leave_extractor.py, implementing leave request OCR field extraction.
7. validator/leave_validator.py, implementing PASS / REVIEW / REJECT validator.
8. POST /api/stamp/leave, implementing leave request scanning, verification, and stamping workflow.
9. Frontend new pages: /applications, /applications/new, /applications/:applicationId.
10. Modify operator console button to "Scan Leave Request and Verify for Stamping."
11. Enhance review and logs pages to display application_id, task_id, risk_score, verification_result.

Must Follow Superpower Mode:
1. Do not perform large-scale refactoring all at once.
2. Complete only one small, verifiable feature point at a time.
3. Run a quick test after completing each phase.
4. If the test fails, fix it first before moving forward.
5. Output modified files, test methods, test results, and next step plan for each phase.

Final Acceptance Must Pass:
1. Normal approved applications can be auto-stamped.
2. Unapproved applications must be REJECTed.
3. Student ID mismatches must be REJECTed.
4. Unclear OCR must go to REVIEW.
5. Duplicate stamping must be REJECTed.
6. QR code tampering must be REJECTed.
7. Existing login, template, camera, calibration, review, and log features must not be broken.
```

## 25. Voice Control Module (Voice Agent)

### 25.1 Architecture Overview

```
User press and hold to speak → Recording → POST /api/voice/chat → Dify voice Q&A workflow
                                              ↓
                              ASR → LLM (Function Calling)
                                         ↓
                              tool_id 1-6 + comment
                                         ↓
              ┌──────────────────────────┴──────────────────────────┐
              ↓                                                    ↓
      tool_id 1-4: Hardware actions                         tool_id 5-6: Database queries
      ├─ 1: arm_home (return to home)                ├─ 5: query_leave_history
      ├─ 2: arm_move (move)                          │   → Query leave records (supports name search)
      ├─ 3: arm_greet (greet)                        └─ 6: query_audit_logs
      └─ 4: stamp_leave_check (stamp)                    → Query successful stamping logs
              ↓                                                    ↓
      Backend background thread execution              LLM summary → Natural language reply
      TTS cache pre-warm → Frontend direct playback
```

### 25.2 Tool Descriptions

| tool_id | Function | Executor | Description |
|---|---|---|---|
| 1 | arm_home | Backend hardware | Robotic arm returns to home position, all servos zeroed |
| 2 | arm_move | Backend hardware | Move robotic arm to specified position |
| 3 | arm_greet | Backend hardware | Wrist raises then lowers, greeting gesture |
| 4 | stamp_leave_check | Backend hardware | Smart stamping (capture → scan → verify → stamp) |
| 5 | query_leave_history | Backend database | Query leave records, supports exact name search, returns student ID + leave count + LLM summary |
| 6 | query_audit_logs | Backend database | Query recent successful stamping records, LLM summarizes into natural language |

### 25.3 Key Files

| File | Description |
|---|---|
| `api/voice.py` | Voice module all logic: execute tools, query database, TTS cache |
| `utils/dify_client.py` | Dify workflow client: voice Q&A + voice.yml TTS |
| `web/src/components/voice-control.tsx` | Frontend recording component, press and hold to speak, release to send |
| `tts_cache/` | TTS audio cache directory, pre-warmed on startup |

### 25.4 Speed Optimization

- **Tools 1-4**: Robotic arm executes in background thread, non-blocking; TTS cache pre-warm (synchronous generation on startup), frontend directly plays base64 audio, skipping `/tts` requests
- **Tools 5-6**: Database query followed by LLM summary, then call `/tts` to generate audio
- **TTS Cache**: On cache miss, synchronously call Dify voice.yml to generate and cache, avoiding repeated calls

### 25.5 Test Commands

Press and hold the voice button to speak, release to auto-send:

| tool_id | Example Command | Effect |
|---|---|---|
| 1 | "Little arm, return to home" | Robotic arm returns + voice reply |
| 3 | "Little arm, wave hello" | Wrist raises and lowers + voice reply |
| 4 | "Little arm, stamp for me" | Starts stamping workflow + voice reply |
| 5 | "Little arm, check Zhang San's leave records" | Query that person's leave history |
| 6 | "Little arm, who has stamped recently" | Query successful stamping records |

### 25.6 API Overview

| Method | Path | Description |
|---|---|---|
| POST | `/api/voice/chat` | Audio → Dify → Execute tool → Return tool_id + comment + audio |
| POST | `/api/voice/tts` | Text → voice.yml TTS → Audio, cache-first |
| GET | `/api/voice/tools/query_leave_history` | Query leave records, supports `name` parameter |
| GET | `/api/voice/tools/query_audit_logs` | Query stamping logs |

---

*Project uses Turborepo Monorepo · Python FastAPI · React 19 · PaddleOCR · MySQL · OpenCV · pyzbar · Robotic Arm Auto-Stamping*
