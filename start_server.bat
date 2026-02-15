@echo off
echo Starting HoneyTrap Backend Server...
c:\Projects\HoneyTrap\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
