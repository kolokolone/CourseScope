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

if not exist "%PY%" (
  echo [INFO] Creating virtual environment: "%VENV_DIR%"
  python -m venv "%VENV_DIR%"
  if errorlevel 1 goto :fail
)

echo [INFO] Installing backend dependencies...
"%PY%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :fail

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
