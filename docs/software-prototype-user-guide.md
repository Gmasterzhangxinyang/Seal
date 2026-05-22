# MEC202 Document Verification Auto-Stamping Robot — Software Prototype User Guide

> **Version:** v1.0 · Last Updated: 2026-05-19  
> **Target Users:** Administrators, Operators, Reviewers  
> **Access URL:** `http://110.42.229.174`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Access & Login](#2-access--login)
3. [Interface Overview](#3-interface-overview)
4. [Console: Document Stamping](#4-console-document-stamping)
5. [Leave Application Management](#5-leave-application-management)
6. [Manual Review](#6-manual-review)
7. [Template Management](#7-template-management)
8. [Audit Log](#8-audit-log)
9. [User Management](#9-user-management)
10. [Robotic Arm Calibration](#10-robotic-arm-calibration)
11. [Voice Control](#11-voice-control)
12. [Statistics Dashboard](#12-statistics-dashboard)
13. [FAQ](#13-faq)

---

## 1. System Overview

This system is a **Document Verification Auto-Stamping Robot** designed for school administrative scenarios. Core capabilities:

- **Document Scanning & OCR Recognition**: Automatically extracts document content after the camera captures a photo
- **Rule-based Verification**: Automatically validates document fields against template rules (required fields, format, type, etc.)
- **Robotic Arm Auto-Stamping**: After verification passes, the WeArm 6-DOF robotic arm automatically positions and stamps
- **Manual Review Loop**: Documents that fail automatic verification enter a review queue for administrator approval
- **Leave Application Full Workflow**: Online submission → Reviewer approval → Download PDF with anti-counterfeiting QR code → Print → Camera verification & stamping
- **Audit Traceability**: Each operation records pre- and post-stamping photos, operator, and timestamp

### User Roles & Permissions

| Role | Username | Password | Accessible Features |
|------|----------|----------|-------------------|
| **Administrator** | `admin` | `admin123` | All features: stamping, leave, review, templates, user management, calibration, statistics |
| **Operator** | `operator` | `operator123` | Console stamping, submit leave applications, view own applications |
| **Reviewer** | `reviewer` | `reviewer123` | Console stamping, approve leave, manual review, view audit log |

---

## 2. Access & Login

### 2.1 Access URL

Open `http://110.42.229.174` in a browser to access the system login page.

### 2.2 Login

1. Enter your username and password on the login page
2. Click the **Login** button
3. After successful login, you will be automatically redirected to the console homepage

### 2.3 Registration

The system supports email registration. Click the **Register** link on the login page and fill in your username, email, and password to create an account. Newly registered users default to the operator role and require manual upgrade by an administrator.

### 2.4 Logout

Click the logout icon (🚪) at the bottom of the sidebar to log out.

---

## 3. Interface Overview

### 3.1 Sidebar Navigation

After logging in, the navigation sidebar appears on the left side of the page. The sidebar is collapsible (click the collapse button in the upper-left corner); when collapsed, only icons are displayed.

Navigation is divided into three groups:

| Group | Menu Items | Permissions |
|-------|-----------|-------------|
| **Common** | Console, Leave Application | Everyone |
| **Review** | Audit Log, Manual Review | Administrator, Reviewer |
| **Management** | Template Management, User Management, Statistics Dashboard, Robotic Arm Calibration | Administrator only |

### 3.2 Language Switching

Click the **English / 中文** button at the bottom of the sidebar to switch the interface language with one click. Both Chinese and English have independently optimized copy and layout.

### 3.3 Connection Status Indicator

The dot next to the title at the top of the sidebar shows the backend connection status:
- **Green**: Connection normal
- **Yellow blinking**: Reconnecting
- **Red**: Connection lost

### 3.4 Page Layout

- **Console page**: Special widescreen layout with live camera feed on the left and operation panel on the right
- **Other pages**: Standard centered layout with a maximum width of 1200px

---

## 4. Console: Document Stamping

The console is the core page of the system, located on the homepage (`/`). It provides two modes: **General Stamping** and **Leave Application Stamping**.

### 4.1 Camera Feed

The left side of the console displays the live MJPEG video stream from the USB camera. Place the A4 document to be stamped flat under the camera and adjust the position so the document appears completely within the frame.

**Camera Switching**: If multiple cameras are connected, you can switch between them at the top of the page.

### 4.2 General Document Stamping

Applicable to various non-leave documents (certificates, forms, etc.) that are automatically verified through template rules.

**Steps:**

1. Place the document under the camera
2. Confirm the mode tab is set to **General**
3. Click the **Stamp** button
4. The system automatically: captures photo → OCR recognition → rule verification
5. Verification passed → Robotic arm stamps automatically → Result displayed
6. Verification failed → Document enters the manual review queue

**Result Feedback:**
- ✅ **Passed**: Stamping successful, pre- and post-stamping photos displayed
- ⏳ **Pending Review**: Verification uncertain, submitted for manual review
- ❌ **Rejected**: Verification failed, specific reasons displayed

### 4.3 Leave Application Stamping (SSE Streaming)

Leave application stamping uses SSE (Server-Sent Events) streaming, with the frontend displaying each step's progress in real time.

**Prerequisites:** The leave application has been approved, and the PDF has been downloaded and printed (see [Chapter 5](#5-leave-application-management)).

**Steps:**

1. Place the printed paper leave application (with QR code) under the camera
2. Switch to **Leave** mode
3. Click the **Stamp** button
4. The system executes via SSE stream, displaying real-time progress:

   ```
   ① Capturing photo...
   ② Scanning QR code → parsing application_id
   ③ GLM-4V visual recognition → extracting student ID, name, date, and other fields
   ④ 10 verification checks:
      - QR code signature verification (HMAC-SHA256)
      - Application record existence
      - Status validation (must be APPROVED)
      - Duplicate stamping detection
      - Student ID / name / type / date consistency
      - OCR confidence assessment
   ⑤ Verification passed → Robotic arm stamps → Status updated to STAMPED
   ⑥ Verification uncertain → Enters manual review queue
   ```

5. After the process completes, the final result and pre- and post-stamping photos are displayed

**Verification Rules Explanation:**

The system performs 10 checks and makes decisions based on cumulative risk scores:
- Hard failure exists (invalid signature, record not found, incorrect status) → **Immediate rejection**
- Risk score ≥ 70 → **Rejected**
- Risk score 40–69 → **Manual review**
- Risk score < 40 → **Auto-approved and stamped**

---

## 5. Leave Application Management

Leave applications follow a complete **online approval + offline stamping** closed-loop process.

### 5.1 Leave Application List (`/applications`)

- **Administrators/Reviewers**: View all leave applications
- **Operators**: View only their own applications

The list displays each application's ID, student name, leave type, dates, and status. Click any row to view details.

### 5.2 New Leave Application (`/applications/new`)

Any logged-in user can submit.

Fill in the following information:
- **Student ID** — Student ID number
- **Name** — Student name
- **Department** — Affiliated department (e.g., "School of Computer Science and Technology")
- **Leave Type** — Sick leave / Personal leave / Other
- **Start Date** — Format: YYYY-MM-DD
- **End Date** — Format: YYYY-MM-DD
- **Reason** — Detailed explanation

After submission, the status is `SUBMITTED` (awaiting approval).

### 5.3 Approval (Administrators/Reviewers Only)

On the leave application detail page (`/applications/{id}`):

1. Review the application content
2. Click **Approve** or **Reject**
3. **After approval**: The system automatically generates a QR code with an HMAC-SHA256 anti-counterfeiting signature, and the application status changes to `APPROVED`
4. **After rejection**: The status changes to `REJECTED`

### 5.4 Download Leave Application PDF

After approval, the detail page displays:
- **QR Code Image**: Anti-tampering signature QR code
- **Download PDF Button**: Click to download the complete leave application PDF with the QR code

Print the PDF to paper, then bring it to the stamping console for physical stamping.

### 5.6 Status Transitions

```
SUBMITTED ──Approved──→ APPROVED ──Stamped──→ STAMPED
     │                      │
     └──Rejected──→ REJECTED └──Stamping failed──→ Review queue
```

---

## 6. Manual Review

When automatic verification is inconclusive (insufficient OCR confidence, partial field matching, etc.), documents enter the manual review queue.

### 6.1 Access Permissions

Only **Administrators** and **Reviewers** can access this feature. Path: `/review`.

### 6.2 Review Operations

1. Switch to the **Pending** tab to view items awaiting review
2. Click any item to expand details:
   - Document capture image
   - OCR-extracted fields
   - Status of each check item (passed/warning/failed)
   - Failure reasons
3. After manual assessment, click **Approve** or **Reject**
4. Approval triggers the stamping process; rejection records the reason

### 6.3 History

Switch to the **All** tab to view all review records (approved, rejected).

---

## 7. Template Management

Only **Administrators** can access this feature. Path: `/admin/templates`.

### 7.1 Template List

Displays all defined document templates. Each row shows the template name, document type, field count, and last updated time.

### 7.2 Create Template

Click **New Template** to enter the editor page (`/admin/templates/new`):

1. Enter the template name (e.g., "Leave Application", "Transcript")
2. Define the field list. Each field includes:
   - **Field Name**: e.g., `student_id`, `name`
   - **Display Name**: Label text, e.g., "Student ID"
   - **OCR Regex**: Regular expression used to extract the field from OCR results
   - **Required**: Whether this is a required field
   - **Validation Rules**: Type checking (number, date, string, etc.)
3. Save the template

### 7.3 Edit & Delete

- Click a template row to enter the editor page and make modifications
- Click the delete button to remove a template (confirmation required)

### 7.4 Export

Each template can be exported as a JSON file for backup or migration.

---

## 8. Audit Log

Only **Administrators** and **Reviewers** can access this feature. Path: `/logs`.

The list displays complete records of each stamping operation:

| Field | Description |
|-------|-------------|
| Time | Operation timestamp |
| Operator | User who performed the stamping |
| Document Type | General / Leave Application |
| Result | Passed / Review / Rejected |
| Pre-stamping Photo | Original document photo |
| Post-stamping Photo | Photo after stamping |

Click any record to view detailed information, including OCR recognition results and verification details.

---

## 9. User Management

Only **Administrators** can access this feature. Path: `/admin/users`.

### 9.1 User List

Displays all registered users, including username, role, and registration time.

### 9.2 Delete User

Click the delete button on a user row to remove the account (administrators cannot delete themselves).

### 9.3 Role Management

User roles default to `operator` at registration. To change a role, currently the administrator needs to make changes at the database level.

---

## 10. Robotic Arm Calibration

Only **Administrators** can access this feature. Path: `/calibration`.

The calibration page is used for debugging and calibrating the WeArm 6-DOF robotic arm.

### 10.1 Individual Servo Control

Each servo (6 total) has an independent slider. Drag the slider to control the servo angle in real time. The PWM value range depends on the robotic arm configuration.

### 10.2 Quick Positioning

Click the preset position buttons to automatically move the robotic arm to the target pose.

### 10.3 Four-Corner Calibration

1. Drag the sliders to move the end of the robotic arm to the four corners of the stamping area
2. Click **Save Corner 1 / Corner 2 / Corner 3 / Corner 4** in sequence
3. The system calculates the interpolation coordinates for stamping based on the four corner positions

### 10.4 Homing

Click the **Home** button to return the robotic arm to its initial position.

---

## 11. Voice Control

The console integrates voice control functionality (ASR + TTS):

- Click the microphone button to start voice input
- Supported voice commands:
  - "Stamp" — Triggers stamping
  - "Leave mode" — Switches to leave application mode
  - "General mode" — Switches to general document mode
- The system announces operation results via text-to-speech (TTS)

---

## 12. Statistics Dashboard

Only **Administrators** can access this feature. Path: `/stats`.

Displays key system operation metrics:

- Total stamps today
- Pass rate / Review rate / Rejection rate
- Distribution by document type
- Operator workload statistics

---

## 13. FAQ

### Q1: No response after clicking Stamp?

Check the status indicator dot next to the sidebar title. Red means the backend connection is lost. Check:
- Whether the robot machine is powered on
- Whether the WireGuard VPN is connected (`ping 10.66.66.2`)
- Whether the backend FastAPI service is running

### Q2: Camera shows a black screen?

- Confirm the camera USB is connected
- Check if another program is using the camera
- Refresh the page and try again

### Q3: Leave application stamping shows "Invalid QR code"?

- Make sure you are using the printed PDF downloaded after approval
- The QR code must be clear and complete, not obscured or damaged
- If the QR code is blurry, try reprinting

### Q4: Low OCR recognition rate?

- Ensure the document is placed flat under the camera with even lighting
- Adjust the `ocr_pattern` regular expression for the corresponding field in Template Management
- Handwritten documents currently have lower recognition rates; printed documents are recommended

### Q5: How to view pre- and post-stamping photos?

After successful stamping, they are displayed directly in the console result area. You can also view pre- and post-stamping photos for historical operations on the **Audit Log** page.

### Q6: Can operators see the review queue?

No. The review queue is only visible to administrators and reviewers. When documents submitted by operators enter review, they must wait for an administrator or reviewer to process them.

### Q7: Some text not translated after switching languages?

The system uses progressive internationalization. If you find untranslated text, please contact the frontend developer to add the corresponding i18n entries.

---

*Turborepo Monorepo · React 19 · FastAPI · GLM-4V · WeArm · WireGuard*
