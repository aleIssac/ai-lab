@echo off
cd /d "%~dp0"
echo Stopping AI Lab...
docker compose down
echo.
echo Stopped. Data in volumes is kept.
pause
