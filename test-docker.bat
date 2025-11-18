@echo off
REM Script de test avec Docker - Simule l'environnement de production
echo ===============================================
echo   MODE TEST DOCKER (Pre-production)
echo ===============================================
echo.

echo [1/2] Arret des serveurs Python locaux...
powershell -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue" 2>nul
timeout /t 2 /nobreak > nul

echo [2/2] Demarrage avec Docker Compose...
cd /d "%~dp0"
docker-compose down 2>nul
docker-compose up --build

echo.
echo ===============================================
echo   SERVEURS DOCKER ARRETES
echo ===============================================
pause
