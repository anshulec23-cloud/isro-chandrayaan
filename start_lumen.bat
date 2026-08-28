@echo off
echo Starting LUMEN Lunar Operations Command...
echo.

echo [1/2] Starting Backend API Server...
start "LUMEN Backend" cmd /k "python -m lumen.api.server"

echo [2/2] Starting Frontend Dashboard...
start "LUMEN Frontend" cmd /k "cd dashboard && npm run dev"

echo.
echo Both servers have been launched in separate windows!
echo The dashboard will be available at http://localhost:5173/
