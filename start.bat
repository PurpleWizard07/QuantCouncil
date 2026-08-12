@echo off
REM QuantCouncil one-click launcher.
REM Double-click this file (or run it) to start Postgres, the API, and the web dashboard.
setlocal
cd /d "%~dp0"

echo === QuantCouncil: starting Postgres (Docker) ===
docker compose --env-file .env -f infra\docker-compose.yml up -d postgres
if errorlevel 1 (
    echo Docker Desktop does not seem to be running. Start Docker Desktop and try again.
    pause
    exit /b 1
)

echo === QuantCouncil: starting API on http://localhost:8000 ===
start "QuantCouncil API" cmd /k "cd /d "%~dp0" && call .venv\Scripts\activate.bat && cd apps\api && uvicorn app.main:app --reload --port 8000"

echo === QuantCouncil: starting web dashboard on http://localhost:3000 ===
start "QuantCouncil Web" cmd /k "cd /d "%~dp0apps\web" && npm run dev"

echo === Waiting for services to come up ===
timeout /t 6 /nobreak >nul

start http://localhost:3000

echo.
echo QuantCouncil is starting in two separate windows (API, Web).
echo Close those windows (or run stop.bat) to shut everything down.
endlocal
