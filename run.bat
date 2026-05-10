@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Go to project root (folder of this script)
cd /d "%~dp0"

REM Start Flask backend
cd /d "%~dp0BACKEND"
start "Flask Server" cmd /k "python server.py"

REM Start Vite frontend
cd /d "%~dp0FRONTEND"
start "Vite Dev" cmd /k "npm run dev"

endlocal