@echo off
setlocal EnableExtensions

cd /d "%~dp0" || goto :fail

set "VENV_DIR=%~dp0.venv"
set "PY=%VENV_DIR%\Scripts\python.exe"

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  goto :fail
)

if exist "%PY%" (
  "%PY%" -c "import sys" >nul 2>&1
  if errorlevel 1 (
    echo [WARN] Existing virtual environment is invalid, recreating it...
    rmdir /S /Q "%VENV_DIR%"
  )
)

if not exist "%PY%" (
  echo [INFO] Creating virtual environment: "%VENV_DIR%"
  python -m venv "%VENV_DIR%"
  if errorlevel 1 goto :fail
)

echo [INFO] Installing backend dependencies...
REM garth-ng uses the same import package as the deprecated garth distribution.
REM Remove the legacy distribution first to avoid a mixed Windows venv.
"%PY%" -m pip uninstall -y garth >nul 2>&1
"%PY%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :fail

REM Avoid bind errors if a stale listener remains on 8000.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  echo [WARN] Existing listener detected on :8000 pid=%%a, stopping it...
  taskkill /F /PID %%a >nul 2>&1
)

echo [INFO] Starting backend: http://127.0.0.1:8000
"%PY%" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto :fail

endlocal
exit /b 0

:fail
echo.
echo [ERROR] Backend launch failed.
pause
endlocal
exit /b 1
