@echo off
title Grocery Portal Server
cd /d "%~dp0"
echo Starting Grocery Admin Portal on http://127.0.0.1:8000/admin ...
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
