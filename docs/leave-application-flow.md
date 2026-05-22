# Leave Application Business Approval Flow

## Role Permissions

| Role | Permissions |
|---|---|
| **admin (Administrator)** | Can approve/reject any leave application, view all pages |
| **reviewer (Approver)** | Can approve/reject any leave application, view audit logs and manual review |
| **operator (Operator)** | Can only view their own applications and application status, **cannot approve/reject** |

## Complete Business Flow

```
Create Application ──→ Approval ──→ Download PDF & Print ──→ Camera Stamp
```

### 1. Create Leave Application
- Any logged-in user submits a leave application at `/applications/new`
- Status changes to `SUBMITTED` (awaiting approval)
- System records `created_by` (creator's username)

### 2. Approval
- **Only admin/reviewer** can see the approve/reject buttons (dual authentication: frontend + backend)
- Backend API: `POST /api/leave-applications/{id}/approve` and `/reject` are protected by `require_role("admin", "reviewer")`
- Approved → status changes to `APPROVED`, a QR code with HMAC signature is generated
- Rejected → status changes to `REJECTED`

### 3. Download & Print
- After approval, the detail page displays the QR code and PDF download link
- API: `GET /api/leave-applications/{id}/download` generates a leave form PDF with QR code
- User prints the paper version of the PDF

### 4. Stamping (Operation Console)
- User places the printed paper leave form under the camera
- Switch to "Leave" mode on the operation console at `/`, then click the stamp button
- Backend SSE streaming execution:
  1. Take photo
  2. Scan QR code → parse `application_id`
  3. GLM-4V visual recognition extracts leave form fields
  4. 10 verification checks (signature verification, status validation, field matching, etc.)
  5. Verification passed → robotic arm stamps → status changes to `STAMPED`
  6. Verification doubtful → push to manual review queue
- API: `POST /api/stamp/leave` (SSE streaming)

## Status Transitions

```
SUBMITTED ──Approved──→ APPROVED ──Stamp Success──→ STAMPED
     │                      │
     └──Rejected──→ REJECTED    └──Stamp Failed──→ Review Queue
```

## Key Files

| Layer | File | Description |
|---|---|---|
| Frontend List | `apps/web/src/pages/LeaveApplicationsPage.tsx` | Leave list, operators can only see their own |
| Frontend Detail | `apps/web/src/pages/LeaveApplicationDetailPage.tsx` | Detail page, approve/reject buttons visible only to admin/reviewer |
| Frontend New | `apps/web/src/pages/NewLeaveApplicationPage.tsx` | New application form |
| Backend API | `apps/backend/api/leave_applications.py` | CRUD, approve, reject, PDF download |
| Backend Stamp | `apps/backend/api/stamp.py` | SSE streaming stamp flow |
| Backend Validation | `apps/backend/validator/leave_validator.py` | 10 verification checks |
| Backend Auth | `apps/backend/api/deps.py` | `require_role()` dependency injection |
| Data Model | `apps/backend/database/models.py` | LeaveApplication table structure |
