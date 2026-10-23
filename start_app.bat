@echo off
title Customer App (Expo)
cd /d "%~dp0mobile"
if not exist node_modules (
  echo First run: installing the app's packages...
  call npm ci
)
echo.
echo Customer app preview
echo  - On this PC: press  w  to open it in the browser (http://localhost:8081)
echo  - On a phone on the same Wi-Fi: install "Expo Go" from the Play Store and scan the QR code below
echo  - Keep start_server.bat running too - the app gets its data from it.
echo.
call npx expo start --port 8081
pause
