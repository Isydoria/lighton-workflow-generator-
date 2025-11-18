@echo off
REM Script de developpement rapide - Python local sans Docker
echo ===============================================
echo   MODE DEVELOPPEMENT (Python local)
echo ===============================================
echo.

echo [1/3] Arret des anciens serveurs...
REM Tuer tous les processus Python
powershell -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue" 2>nul
REM Liberer les ports 8000 et 3000 si occupes
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak > nul

echo [2/3] Demarrage du backend API (port 8000)...
cd /d "%~dp0"
start "Backend API - Dev" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn api.index:app --port 8000"

timeout /t 3 /nobreak > nul

echo [3/3] Demarrage du frontend (port 3000)...
start "Frontend - Dev" cmd /k "python -m http.server 3000"

echo.
echo ===============================================
echo   SERVEURS DEMARRES EN MODE DEV
echo   Frontend: http://localhost:3000
echo   Backend API: http://localhost:8000/docs
echo ===============================================
echo.
echo Fermez les fenetres pour arreter les serveurs.
pause
