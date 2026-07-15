@echo off
setlocal EnableExtensions

cd /d "%~dp0" || goto :fail

if not defined COURSESCOPE_DATA_DIR set "COURSESCOPE_DATA_DIR=%~dp0data"
echo [INFO] Runtime data: "%COURSESCOPE_DATA_DIR%"

REM Stop the previous dev server before checking or repairing its virtualenv.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  echo [WARN] Existing listener detected on :8000 pid=%%a, stopping it...
  taskkill /F /PID %%a >nul 2>&1
)

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
"%PY%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :fail

REM garth and garth-ng share the same import namespace. A previous uninstall can
REM leave garth-ng metadata behind while deleting its API files. Repair only
REM when the exact API used by CourseScope is unavailable.
"%PY%" -c "import garth; C=getattr(getattr(garth, 'http', None), 'Client', None); assert callable(getattr(garth, 'resume', None)); assert callable(C); assert callable(getattr(C, 'login', None)); assert callable(getattr(C, 'resume_login', None)); assert getattr(garth, 'client', None) is not None" >nul 2>&1
if errorlevel 1 (
  echo [WARN] Incomplete or conflicting garth installation detected, repairing garth-ng...
  "%PY%" -m pip uninstall -y garth garth-ng >nul 2>&1
  "%PY%" -m pip install --no-cache-dir "garth-ng==1.1.0"
  if errorlevel 1 goto :fail
  "%PY%" -c "import garth; C=getattr(getattr(garth, 'http', None), 'Client', None); assert callable(getattr(garth, 'resume', None)); assert callable(C); assert callable(getattr(C, 'login', None)); assert callable(getattr(C, 'resume_login', None)); assert getattr(garth, 'client', None) is not None" >nul 2>&1
  if errorlevel 1 goto :fail
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
