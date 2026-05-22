# Leave Application Feature Summary

> Last updated: 2026/05/19

---

## 1. Overview

The leave application feature in this project is a complete closed-loop system combining **online leave application submission + offline verification and stamping**. Students submit leave applications online; after an administrator approves the request, a leave form with an HMAC-signed QR code is generated. The operator scans the QR code at the stamping robot, uses OCR to recognize the paper content and compares it against the online record. Stamping is only allowed after successful verification.

---

## 2. Roles and Permissions

| Role | Permissions |
|---|---|
| **admin (Administrator)** | Can approve/reject any leave application, access all pages |
| **reviewer (Reviewer)** | Can approve/reject any leave application, view audit logs and perform manual reviews |
| **operator (Operator)** | Can only view their own applications and application status, **cannot approve/reject** |

---

## 3. Business Flow

```
Create Application → Approve → Download PDF & Print → Camera Stamping
```

1. **Create Application**: Any logged-in user submits a leave application at `/applications/new`; status changes to `SUBMITTED`
2. **Approve**: After admin/reviewer approval, status changes to `APPROVED` and an HMAC-signed QR code is generated
3. **Download & Print**: After approval, the detail page displays the QR code and a PDF download link
4. **Stamping**: The operator console switches to "leave" mode. Click the stamp button to execute via SSE streaming: take photo → scan QR code → GLM-4V visual recognition → 10 verification checks → stamp or enter review

---

## 4. Status Flow

```
SUBMITTED ──Approved──→ APPROVED ──Stamped──→ STAMPED
     │                      │
     └──Rejected──→ REJECTED └──Stamp Failed──→ Review Queue
```

---

## 5. Key File Listing

### 5.1 Backend

| File | Description |
|---|---|
| `apps/backend/api/leave_applications.py` | Leave application CRUD, approval, rejection, PDF download |
| `apps/backend/api/stamp.py` | SSE streaming stamping flow (`/stamp/leave`) |
| `apps/backend/validator/leave_validator.py` | 10 verification checks, PASS/REVIEW/REJECT decision |
| `apps/backend/vision/leave_extractor.py` | OCR field extraction (application ID, name, student ID, dates, etc.) |
| `apps/backend/utils/qr_sign.py` | HMAC-SHA256 QR code signing and verification |
| `apps/backend/database/models.py` | `LeaveApplication`, `StampTask`, `VerificationResult` models |

### 5.2 Frontend

| File | Description |
|---|---|
| `apps/web/src/pages/LeaveApplicationsPage.tsx` | Leave application list page |
| `apps/web/src/pages/NewLeaveApplicationPage.tsx` | New application form page |
| `apps/web/src/pages/LeaveApplicationDetailPage.tsx` | Application detail page |
| `apps/web/src/i18n/locales/zh/applications.json` | Chinese internationalization |
| `apps/web/src/i18n/locales/en/applications.json` | English internationalization |

### 5.3 Documentation

| File | Description |
|---|---|
| `docs/leave-application-flow.md` | Business approval flow documentation |
| `doc/README_leave_request_stamping.md` | Complete project documentation |

---

## 6. Database Models

### 6.1 `leave_applications` — Leave Application Table

| Field | Type | Description |
|---|---|---|
| `id` | INT | Primary key |
| `application_id` | VARCHAR(64) | Unique application ID, format `LEAVE-YYYYMMDD-NNNN` |
| `student_id` | VARCHAR(20) | Student ID |
| `student_name` | VARCHAR(50) | Student name |
| `dept` | VARCHAR(100) | Department |
| `leave_type` | VARCHAR(50) | Leave type (sick leave, personal leave, etc.) |
| `start_date` | VARCHAR(30) | Start date |
| `end_date` | VARCHAR(30) | End date |
| `reason` | TEXT | Reason for leave |
| `status` | VARCHAR(30) | SUBMITTED / APPROVED / REJECTED / STAMPED |
| `qr_content` | TEXT | QR code payload string |
| `approved_by` | VARCHAR(50) | Approver |
| `approved_at` | VARCHAR(30) | Approval time |
| `stamped_at` | VARCHAR(30) | Stamping time |
| `created_by` | VARCHAR(50) | Creator |
| `created_at` | VARCHAR(30) | Creation time |
| `updated_at` | VARCHAR(30) | Update time |

### 6.2 `stamp_tasks` — Stamp Task Table

| Field | Type | Description |
|---|---|---|
| `task_id` | VARCHAR(64) | Unique task ID |
| `application_id` | VARCHAR(64) | Associated leave application ID |
| `operator_id` | VARCHAR(50) | Operator |
| `doc_type` | VARCHAR(50) | Fixed as `leave` |
| `status` | VARCHAR(30) | CREATED / PASS / REVIEW / REJECT / STAMPED, etc. |
| `decision` | VARCHAR(30) | PASS / REVIEW / REJECT |
| `risk_score` | INT | Risk score |
| `before_img` | VARCHAR(500) | Pre-stamp image path |
| `after_img` | VARCHAR(500) | Post-stamp image path |
| `qr_content` | TEXT | QR code content |
| `extracted_fields` | TEXT | OCR extracted fields JSON |
| `verification_result` | TEXT | Verification result JSON |
| `error_message` | TEXT | Error message |

### 6.3 `verification_results` — Verification Result Table

| Field | Type | Description |
|---|---|---|
| `task_id` | VARCHAR(64) | Associated task ID |
| `check_name` | VARCHAR(100) | Check item name |
| `result` | VARCHAR(30) | pass / warn / fail |
| `score` | INT | Risk score |
| `reason` | TEXT | Description |

---

## 7. API Endpoints

### 7.1 Leave Applications `/api/leave-applications`

| Method | Path | Description | Permission |
|---|---|---|---|
| POST | `/` | Create leave application | Authenticated user |
| GET | `/` | Get application list | admin/reviewer: all; operator: own only |
| GET | `/{application_id}` | Get application detail | Authenticated user |
| POST | `/{application_id}/approve` | Approve application | admin/reviewer |
| POST | `/{application_id}/reject` | Reject application | admin/reviewer |
| GET | `/{application_id}/qr` | Get QR code payload | Authenticated user |
| GET | `/{application_id}/qr/image` | Get QR code PNG image | Authenticated user |
| GET | `/{application_id}/download` | Download leave form PDF | Authenticated user |

### 7.2 Stamping `/api/stamp`

| Method | Path | Description |
|---|---|---|
| POST | `/stamp` | General stamping endpoint |
| POST | `/stamp/leave` | Leave form verification and stamping (SSE streaming) |

---

## 8. Verification Logic

`POST /api/stamp/leave` performs 10 checks:

| # | Check Item | Rule | Fail Score |
|---|---|---|---:|
| 1 | QR code signature verification | HMAC-SHA256 payload verification | 70 |
| 2 | Application record existence | application_id must exist | 70 |
| 3 | Application status verification | Status must be APPROVED | 70 |
| 4 | Duplicate stamp detection | stamped_at must be empty | 70 |
| 5 | Student ID consistency | OCR student ID = application record student ID | 70 |
| 6 | Name consistency | Minor differences allowed (spaces, case) | 40 |
| 7 | Leave type consistency | OCR type = application record type | 40 |
| 8 | Date consistency | Start/end dates must match | 40 |
| 9 | Reason field verification | Reason field must not be empty | 25 |
| 10 | OCR confidence | >=0.85 PASS, 0.65-0.85 REVIEW, <0.65 REJECT | 40 |

**Decision rules:**

- Any hard fail (failed item with score 70) → REJECT
- `risk_score >= 70` → REJECT
- `risk_score >= 40` → REVIEW
- `risk_score < 40` → PASS

---

## 9. QR Code Signing

`apps/backend/utils/qr_sign.py` implements HMAC-SHA256 tamper protection:

```python
# Generate
payload = create_leave_qr_payload(application_id, student_id)
# payload = {"application_id": "...", "student_id": "...", "nonce": "...", "sig": "..."}
qr_content = qr_payload_to_string(payload)  # Serialize and generate QR code

# Verify
payload = qr_string_to_payload(qr_string)
verify_qr_payload(payload)  # Returns True/False
```

---

## 10. Frontend Pages

| Path | Page | Description |
|---|---|---|
| `/applications` | LeaveApplicationsPage | Leave application list |
| `/applications/new` | NewLeaveApplicationPage | Create new leave application |
| `/applications/:id` | LeaveApplicationDetailPage | Application detail + approval buttons |

After switching the operator console at `/` to "leave" mode, clicking the stamp button calls `POST /api/stamp/leave`, with SSE streaming display: take photo → scan QR code → GLM-4V recognition → verification results → stamp/review/reject.

---

## 11. Sample Images

Sample leave form image: `apps/backend/example_images/leave_example.jpg`

Audit image directory: `apps/backend/audit_images/` (contains numerous `leave_before.jpg`, `leave_pre_stamp.jpg`, `leave_after.jpg`)

---

## 12. Related Configuration

Key configuration in `apps/backend/config.py`:

- `ARM_TYPE` — Robot arm type (`wearm` / `hiwonder`)
- `SIMULATION_MODE` — Simulation mode; recommended True during development
- `SECRET_KEY` — HMAC signing key
- `VLM_API_KEY` / `VLM_BASE_URL` / `VLM_MODEL` — GLM-4V visual model configuration
