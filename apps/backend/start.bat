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

echo [Backend] Starting...
start "StampRobot-Backend" cmd /c "uv run python -m api.main"

echo [Frontend] Starting...
cd ..\web
call npx vite --open
