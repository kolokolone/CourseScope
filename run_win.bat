@echo off
setlocal

rem NOTE: This script spawns two new windows (API + Frontend) and may exit quickly.
rem If your launcher window closes before you can read errors, run from an existing cmd:
rem   cd /d "%~dp0" && run_win.bat

rem Always relaunch into a dedicated cmd window, so double-clicking (Explorer) and
rem running from terminals behave consistently.
if /i not "%~1"=="--child" (
    start "CourseScope Launcher" cmd /k "\"%~f0\" --child"
    exit /b 0
)

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || goto :fail

set "VENV_DIR=%PROJECT_DIR%.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Creation de l'environnement virtuel...
    py -3.11 -m venv "%VENV_DIR%" 2>nul || py -3 -m venv "%VENV_DIR%" 2>nul || python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement virtuel.
        goto :fail
    )
)

if not exist "%PYTHON_EXE%" (
    echo [ERREUR] Python venv introuvable: "%PYTHON_EXE%"
    goto :fail
)

if exist "%PROJECT_DIR%requirements.txt" (
    echo [INFO] Installation des dependances...
    "%PYTHON_EXE%" -m pip install -r "%PROJECT_DIR%requirements.txt"
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation des dependances.
        pause
        exit /b 1
    )
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Node.js (npm) introuvable. Installe Node.js pour lancer le frontend.
    pause
    exit /b 1
)

echo [INFO] Lancement de l'API FastAPI (nouvelle stack)...
start "CourseScope API" /D "%PROJECT_DIR%" cmd /k "\"%PYTHON_EXE%\" -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000"

echo [INFO] Lancement du frontend Next.js (nouvelle stack)...
start "CourseScope Frontend" /D "%PROJECT_DIR%frontend" cmd /k "set NEXT_PUBLIC_API_URL=http://localhost:8000 ^&^& npm install ^&^& npm run dev"

echo [INFO] Ouverture du navigateur: http://localhost:3000
start "" "http://localhost:3000"

echo.
echo [INFO] L'API et le frontend ont ete lances dans deux fenetres separees.
echo [INFO] Ferme ces fenetres pour arreter les serveurs.
pause

endlocal
exit /b 0

:fail
echo.
echo [ERREUR] Le script s'est arrete. Voir les messages ci-dessus.
pause
endlocal
exit /b 1
