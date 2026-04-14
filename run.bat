@echo off

echo Starting Backend...
start cmd /k "cd BACKEND && python run.py"

echo Starting Frontend...
start cmd /k "cd FRONTEND && npm run dev"

echo All services started.
pause