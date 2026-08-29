@echo off
set ROOT=%~dp0
cd /d "%ROOT%"

echo Starting NTU Exchange Planner...
echo.

start "NTU Exchange API" cmd /k "cd /d "%ROOT%backend" && .venv\Scripts\python.exe -m uvicorn api.chat:app --app-dir src --port 8000"
timeout /t 2 /nobreak >nul
start "NTU Exchange UI" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo API:  http://127.0.0.1:8000
echo UI:   http://localhost:3000
echo Close the two CMD windows (or press Ctrl+C in each) to stop.
start "" http://localhost:3000
