@echo off
REM QuantCouncil one-click launcher.
REM Double-click this file (or run it) to start Postgres, the API, and the web dashboard.
setlocal
cd /d "%~dp0"

echo === QuantCouncil: checking Docker Desktop ===
docker info >nul 2>&1
if not errorlevel 1 (
    echo Docker Desktop is already running.
    goto qc_docker_ready
)

echo Docker Desktop is not running -- starting it now...
set "DOCKER_DESKTOP_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not exist "%DOCKER_DESKTOP_EXE%" (
    echo Could not find Docker Desktop at "%DOCKER_DESKTOP_EXE%".
    echo Start Docker Desktop manually, then re-run this script.
    pause
    exit /b 1
)
start "" "%DOCKER_DESKTOP_EXE%"

echo Waiting for Docker Desktop to finish starting -- this can take a minute or two...
set /a "_qc_wait=0"

:qc_wait_for_docker
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if not errorlevel 1 goto qc_docker_started
set /a "_qc_wait+=3"
if %_qc_wait% GEQ 120 (
    echo.
    echo Docker Desktop did not finish starting within 2 minutes.
    echo Check the Docker Desktop window for errors, then re-run this script.
    pause
    exit /b 1
)
echo   ...still waiting ^(%_qc_wait%s^)
goto qc_wait_for_docker

:qc_docker_started
echo Docker Desktop is up.

:qc_docker_ready

echo === QuantCouncil: starting Postgres (Docker) ===
docker compose --env-file .env -f infra\docker-compose.yml up -d postgres
if errorlevel 1 (
    echo Failed to start the Postgres container. See the output above for details.
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
