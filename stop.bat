@echo off
setlocal
title Federated Cyber Shield Stopper

echo ======================================================================
echo    STOPPING FEDERATED CYBER SHIELD (FCS) SERVERS
echo ======================================================================
echo.

set KILLED=0

REM Terminate port 8000 (Backend API)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [*] Stopping FCS Backend API - PID %%a on port 8000
    taskkill /F /PID %%a >nul 2>&1
    set KILLED=1
)

REM Terminate port 5173 (Frontend Dashboard)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo [*] Stopping FCS Frontend Dashboard - PID %%a on port 5173
    taskkill /F /PID %%a >nul 2>&1
    set KILLED=1
)

if "%KILLED%"=="1" (
    echo.
    echo [+] Successfully stopped FCS background servers.
) else (
    echo [*] No running FCS instances found on ports 8000 or 5173.
)

echo.
ping -n 3 127.0.0.1 >nul 2>&1
