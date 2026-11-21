@echo off
setlocal

echo ========================================================
echo        LUMEN - Lunar Multi-Sensor Registration
echo ========================================================
echo.
echo Starting Demo Environment...
echo.

:: 1. Navigate to dashboard and build
echo [1/3] Building frontend dashboard...
cd dashboard
call npm install
call npm run build
if %errorlevel% neq 0 (
    echo Failed to build dashboard.
    exit /b %errorlevel%
)
cd ..

:: 2. Start FastAPI Backend in the background
echo [2/3] Starting backend server on port 8000...
start "LUMEN Backend" cmd /k "python -m uvicorn lumen.api.server:app --port 8000"

:: 3. Wait for backend to be ready
echo [3/3] Waiting for backend to become healthy...
:poll
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    ping -n 2 127.0.0.1 >nul
    goto poll
)

echo.
echo Backend is healthy! Opening dashboard in browser...
start http://localhost:8000/

echo.
echo Demo is running. Close the "LUMEN Backend" command prompt window to stop the server.
echo ========================================================
