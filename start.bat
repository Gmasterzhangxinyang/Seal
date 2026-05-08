@echo off
title StampRobot Dev

echo ==========================================
echo   StampRobot - Dev Mode
echo   Backend:  http://127.0.0.1:5001
echo   Frontend: http://localhost:5173
echo   Ctrl+C to stop
echo ==========================================
echo.

:: Kill stale processes on port 5001 / 5173
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5001 .*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5173 .*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Start backend in background
echo [Backend] Starting...
start /B "" python -m api.main

:: Poll until port 5001 is listening (max 60s)
set WAITED=0
:waitloop
netstat -aon 2>nul | findstr ":5001 .*LISTENING" >nul 2>&1
if not errorlevel 1 goto backend_ready
timeout /t 2 /nobreak >nul
set /a WAITED+=2
if %WAITED% GEQ 60 (
    echo [Backend] Timeout - waited 60s, giving up
    pause
    exit /b 1
)
goto waitloop
:backend_ready
echo [Backend] Ready!

:: Start frontend
echo [Frontend] Starting...
cd frontend
call npm run dev
