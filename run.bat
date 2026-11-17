@echo off
setlocal
title Federated Cyber Shield Launcher

echo ======================================================================
echo    FEDERATED CYBER SHIELD (FCS) v1.2 - SYSTEM LAUNCHER
echo ======================================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM 1. Check Python runtime
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ and add it to PATH.
    echo.
    pause
    exit /b 1
)
echo [OK] Python runtime detected.

REM 2. Check Node / npm (must use call because npm is a .cmd script)
call npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm / Node.js is not found in your system PATH.
    echo Please install Node.js v18+ and add it to PATH.
    echo.
    pause
    exit /b 1
)
echo [OK] Node.js / npm runtime detected.

REM 3. Terminate any previous lingering processes on ports 8000 and 5173
echo [*] Checking for existing processes on ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [*] Terminating lingering process on port 8000 - PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo [*] Terminating lingering process on port 5173 - PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM 4. Seed database with demo accounts and data
echo [*] Initializing SQLite database and seeding demo accounts...
python -m tools.fcs_cli demo seed
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Database seed encountered an issue, proceeding anyway...
)

REM 5. Launch FastAPI Backend Server on port 8000 in dedicated window
echo [*] Launching FastAPI Backend Server on http://127.0.0.1:8000 ...
cd /d "%ROOT_DIR%"
start "FCS Backend API [Port 8000]" cmd /k "title FCS Backend API [Port 8000] & python -u -m tools.fcs_cli api start --port 8000"

REM 6. Launch React SOC Dashboard on port 5173 in dedicated window
echo [*] Launching React SOC Dashboard on http://127.0.0.1:5173 ...
cd /d "%ROOT_DIR%apps\security-dashboard"
start "FCS Security Dashboard [Port 5173]" cmd /k "title FCS Security Dashboard [Port 5173] & npm run dev"

REM 7. Return to project root directory
cd /d "%ROOT_DIR%"

REM 8. Wait for services to initialize
echo [*] Waiting 4 seconds for services to bind...
ping -n 5 127.0.0.1 >nul 2>&1

REM 9. Open default web browser
echo [*] Opening Dashboard in your default web browser...
start http://localhost:5173/

echo.
echo ======================================================================
echo    FEDERATED CYBER SHIELD IS NOW RUNNING!
echo ======================================================================
echo.
echo    [1] Frontend Dashboard:   http://localhost:5173/
echo    [2] Backend API (Live):   http://localhost:8000/
echo    [3] OpenAPI Swagger Docs: http://localhost:8000/docs
echo    [4] API Health Check:     http://localhost:8000/healthz
echo.
echo  ----------------------------------------------------------------------
echo    DEMONSTRATION CREDENTIALS:
echo  ----------------------------------------------------------------------
echo    - Security Responder: username: responder_alpha ^| password: FcsDemo2026!
echo    - Security Analyst:   username: analyst_alpha   ^| password: FcsDemo2026!
echo    - Tenant Admin:       username: admin_alpha     ^| password: FcsDemo2026!
echo  ----------------------------------------------------------------------
echo.
echo  >>> Both services are running in their own dedicated windows.
echo  >>> Keep this window open while using the application.
echo.

:MENU
echo  Type STOP or Q and press Enter to shutdown all servers.
set /p USER_INPUT="fcs> "
if /i "%USER_INPUT%"=="q" goto SHUTDOWN
if /i "%USER_INPUT%"=="quit" goto SHUTDOWN
if /i "%USER_INPUT%"=="stop" goto SHUTDOWN
if /i "%USER_INPUT%"=="exit" goto SHUTDOWN
echo.
echo  [!] Unrecognized command '%USER_INPUT%'. Both servers are still running.
goto MENU

:SHUTDOWN
echo.
echo [*] Shutting down services...
call "%ROOT_DIR%stop.bat"
