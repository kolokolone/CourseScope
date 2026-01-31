@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || goto :fail

set "VENV_DIR=%PROJECT_DIR%.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"

rem Usage:
rem   run_win.bat            -> start API + frontend in two windows
rem   run_win.bat --smoke    -> quick non-interactive checks (no dev servers)

if /i "%~1"=="--smoke" goto :smoke

echo [INFO] Project: "%PROJECT_DIR%"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Creation de l'environnement virtuel...
    py -3.11 -m venv "%VENV_DIR%" 2>nul || py -3 -m venv "%VENV_DIR%" 2>nul || python -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
)
if not exist "%PYTHON_EXE%" (
    echo [ERREUR] Python venv introuvable: "%PYTHON_EXE%"
    goto :fail
)

echo [INFO] Installation des dependances Python...
"%PYTHON_EXE%" -m pip install -r "%PROJECT_DIR%requirements.txt" || goto :fail

where node >nul 2>&1 || goto :node_missing
where npm >nul 2>&1 || goto :node_missing
if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERREUR] Dossier frontend introuvable: "%FRONTEND_DIR%"
    goto :fail
)

echo [INFO] Lancement de l'API (fenetre dediee): http://localhost:8000
start "CourseScope API" /D "%PROJECT_DIR%" cmd /k "\"%PYTHON_EXE%\" -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000"

echo [INFO] Attente backend: http://127.0.0.1:8000/health
"%PYTHON_EXE%" "%PROJECT_DIR%scripts\wait_for_http_200.py" "http://127.0.0.1:8000/health" --timeout 25 || (
  echo [ERREUR] Backend non disponible (port 8000). Verifie la fenetre "CourseScope API".
  goto :fail
)

echo [INFO] Lancement du Frontend (fenetre dediee): http://localhost:3000
start "CourseScope Frontend" /D "%FRONTEND_DIR%" cmd /k "if not exist node_modules\ (if exist package-lock.json (npm ci||npm install) else (npm install)) else (echo [INFO] node_modules present - skip install) && npm run dev"

echo [INFO] Ouverture du navigateur: http://localhost:3000
start "" "http://localhost:3000"

echo.
echo [INFO] Deux fenetres ont ete lancees (API + Frontend).
echo [INFO] Si une fenetre se ferme, elle contient la cause (erreur).
pause

endlocal
exit /b 0

:smoke
echo [SMOKE] Verifications prerequis...
where node >nul 2>&1 || goto :node_missing
where npm >nul 2>&1 || goto :node_missing
if not exist "%PROJECT_DIR%requirements.txt" (
    echo [SMOKE][ERREUR] requirements.txt introuvable
    goto :fail
)
if not exist "%FRONTEND_DIR%\package.json" (
    echo [SMOKE][ERREUR] frontend/package.json introuvable
    goto :fail
)
echo [SMOKE] OK
endlocal
exit /b 0

:node_missing
echo [ERREUR] Node.js (node/npm) introuvable. Installe Node.js (recommande: Node 20 LTS).
pause
endlocal
exit /b 1

:fail
echo.
echo [ERREUR] Le script a echoue. Relance dans un terminal pour voir les messages:
echo   cd /d "%PROJECT_DIR%" ^&^& run_win.bat
pause
endlocal
exit /b 1
