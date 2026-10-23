@echo off
title Grocery Portal Server
cd /d "%~dp0"
echo Starting Grocery Admin Portal on http://127.0.0.1:8000/admin ...
rem watchfiles restarts the server whenever app\ changes (and force-kills it if it hangs),
rem which is more reliable on Windows than uvicorn's own --reload.
".venv\Scripts\python.exe" -m watchfiles --filter python --sigint-timeout 3 --sigkill-timeout 2 ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000" app
pause
