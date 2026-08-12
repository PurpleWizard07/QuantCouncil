@echo off
REM QuantCouncil one-click shutdown.
REM Closes the API/Web windows started by start.bat and stops the Postgres container
REM (data is preserved in the Docker volume; nothing is deleted).
setlocal
cd /d "%~dp0"

echo === QuantCouncil: stopping web dashboard ===
taskkill /FI "WINDOWTITLE eq QuantCouncil Web*" /T /F >nul 2>&1

echo === QuantCouncil: stopping API ===
taskkill /FI "WINDOWTITLE eq QuantCouncil API*" /T /F >nul 2>&1

echo === QuantCouncil: stopping Postgres (Docker) ===
docker compose --env-file .env -f infra\docker-compose.yml stop postgres

echo Done.
endlocal
