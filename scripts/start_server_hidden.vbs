' Launches the pos_backend FastAPI server with no visible console window.
' Used by the "POS Backend Server" Scheduled Task (fires at user logon) so
' http://127.0.0.1:8000 is already up by the time the browser restores its tabs.
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "G:\pos_backend\pos_backend"
WshShell.Run """G:\pos_backend\pos_backend\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 127.0.0.1 --port 8000", 0, False
