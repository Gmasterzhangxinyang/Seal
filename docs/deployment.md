# Deployment Guide

## 1. Prerequisites

- **Python** >= 3.11
- **Node.js** >= 18 (with pnpm)
- **MySQL** >= 5.7.7 (utf8mb4 support)
- **Git**
- (Optional) **CH340 USB driver** — for WeArm serial communication

## 2. Install MySQL

### Windows

1. Download [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)
2. Select "Server only" during installation, and set the root password
3. After installation, confirm that the MySQL service has started

### Verify Installation

```bash
mysql -u root -p
# After entering the root password, you should enter the MySQL command line
```

## 3. Create Database and User

Log in as root and run:

```sql
CREATE DATABASE stamp_robot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'stamp_robot'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stamp_robot.* TO 'stamp_robot'@'localhost';
FLUSH PRIVILEGES;
```

## 4. Clone and Install Dependencies

```bash
git clone <repo-url> MEC202
cd MEC202
pnpm install
cd apps/backend
uv sync
```

## 5. Configure Environment Variables

Copy the sample env file and fill in your values:

```bash
cp apps/backend/.env.sample apps/backend/.env
```

Required fields in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | MySQL host | `localhost` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_USER` | MySQL user | `stamp_robot` |
| `DB_PASSWORD` | MySQL password | *(empty)* |
| `DB_NAME` | Database name | `stamp_robot` |
| `SECRET_KEY` | JWT signing key | `dev-fallback-key` |

Optional fields (enable AI/voice features):

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | Alibaba Cloud DashScope (ASR) |
| `OPENAI_API_KEY` | OpenAI Whisper (ASR fallback) |
| `ZHIPU_API_KEY` | Zhipu GLM (VLM / OCR / Chat) |
| `VLM_MODEL` | VLM model name (default `glm-4.6v`) |
| `CHAT_MODEL` | Chat model name (default `glm-4-flash`) |
| `FISH_AUDIO_API_KEY` | Fish Audio TTS |
| `DIFY_API_KEY` | Dify workflow (leave approval AI) |
| `DIFY_BASE_URL` | Dify API base URL |
| `DMS_BASE_URL` | Document management system (leave empty to skip) |
| `AURORA_CHAT_URL` | Aurora chat assistant |

## 6. Run Database Migration

```bash
cd apps/backend
alembic upgrade head
```

Seed data (demo personnel, default accounts, document templates) is **automatically** initialized on first backend startup.

## 7. Start the Service

### Option A: Turbo (recommended)

From the project root:

```bash
pnpm dev
```

### Option B: dev.bat (Windows)

```bash
dev.bat
```

### Option C: Start individually

```bash
# Backend (port 5001)
cd apps/backend
uv run python -m api.main

# Frontend (port 5173)
cd apps/web
pnpm dev
```

Access URL: **http://localhost:5173**

## 8. Hardware Setup (Optional)

### WeArm Robotic Arm

- Connect via CH340 USB-to-serial adapter
- Default serial port: `COM10` (configurable via `SERIAL_PORT` in `.env`)
- Baud rate: `115200`
- The backend auto-detects CH340 devices by VID/PID

### Camera

- OpenCV auto-detects cameras (index 0-4)
- Supports MSMF and DSHOW backends on Windows
- Resolution: 1920x1080 MJPG

### Simulation Mode

Set `SIMULATION_MODE=true` in `.env` to run without physical hardware (no serial port, no camera).

## 9. Database Migration Management

```bash
cd apps/backend

# Check current migration status
alembic current

# View migration history
alembic history

# Generate a new migration script (after modifying ORM models)
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Roll back one version
alembic downgrade -1
```

## 10. Reset Database

```bash
cd apps/backend
python reset_db.py
```

This drops and recreates all tables, runs migrations, and re-seeds demo data.

## Default Accounts

| Account | Password | Role |
|---------|----------|------|
| admin | admin123 | Administrator |
| operator1 | op123 | Operator |
| reviewer1 | reviewer123 | Reviewer |

## FAQ

**Q: `Can't connect to MySQL server`?**
A: Check whether the MySQL service is running and whether the credentials in `.env` are correct.

**Q: `Access denied for user`?**
A: Confirm that you have executed the `GRANT` statement in step 3 and that `DB_PASSWORD` in `.env` matches.

**Q: `Unknown charset 'utf8mb4'`?**
A: utf8mb4 is only supported in MySQL 5.7.7+. Please upgrade MySQL.

**Q: `No module named 'xxx'`?**
A: Run `uv sync` in `apps/backend` to install all dependencies.

**Q: Serial port not found?**
A: Install the [CH340 driver](http://www.wch-ic.com/downloads/CH341SER_EXE.html), then verify the port in Device Manager. Update `SERIAL_PORT` in `.env` accordingly.

**Q: How to add personnel data?**
```sql
USE stamp_robot;
INSERT INTO personnel (id_number, name, dept, role)
VALUES ('20210099', 'Your Name', 'Computer Science', 'student');
```
