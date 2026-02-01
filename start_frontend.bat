@echo off
setlocal EnableExtensions

cd /d "%~dp0" || goto :fail

where node >nul 2>&1
if errorlevel 1 goto :node_missing

where npm >nul 2>&1
if errorlevel 1 goto :node_missing

if not exist "%~dp0frontend\package.json" (
  echo [ERROR] Missing frontend\package.json
  goto :fail
)

pushd "%~dp0frontend" || goto :fail

if not exist "node_modules\" (
  echo [INFO] Installing frontend dependencies...
  if exist "package-lock.json" (
    call npm ci || call npm install
  ) else (
    call npm install
  )
  if errorlevel 1 goto :fail
)

echo [INFO] Starting frontend: http://localhost:3000
call npm run dev
if errorlevel 1 goto :fail

popd
endlocal
exit /b 0

:node_missing
echo [ERROR] Node.js/npm not found in PATH.
pause
endlocal
exit /b 1

:fail
echo.
echo [ERROR] Frontend launch failed.
pause
popd >nul 2>&1
endlocal
exit /b 1
