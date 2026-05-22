@echo off
title StampRobot Dev

echo ==========================================
echo   StampRobot - Dev Mode
echo   Backend:  http://127.0.0.1:5001
echo   Frontend: http://localhost:5173
echo   Ctrl+C to stop
echo ==========================================
echo.

cd /d "%~dp0"

echo [Backend] Starting in new window...
start "StampRobot-Backend" cmd /k "cd /d "%~dp0apps\backend" && uv run python -m api.main"

timeout /t 3 /nobreak >nul

echo [Frontend] Starting...
cd apps\web
call pnpm dev
