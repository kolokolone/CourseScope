@echo off
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || goto :fail

set "VENV_DIR=%PROJECT_DIR%.venv"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Creation de l'environnement virtuel...
    py -3.11 -m venv "%VENV_DIR%" 2>nul || py -3 -m venv "%VENV_DIR%" 2>nul || python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement virtuel.
        goto :fail
    )
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERREUR] Impossible d'activer l'environnement virtuel.
    pause
    exit /b 1
)

if exist "%PROJECT_DIR%requirements.txt" (
    echo [INFO] Installation des dependances Python...
    pip install -r "%PROJECT_DIR%requirements.txt"
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation des dependances Python.
        pause
        exit /b 1
    )
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Node.js n'est pas installe. Installez-le puis relancez le script.
    pause
    exit /b 1
)

set "PM=npm"
where pnpm >nul 2>nul
if not errorlevel 1 set "PM=pnpm"

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERREUR] Dossier frontend introuvable.
    goto :fail
)

echo [INFO] Lancement de l'API FastAPI...
start "CourseScope API" /D "%PROJECT_DIR%" cmd /k ""%VENV_DIR%\Scripts\python.exe" -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000"

echo [INFO] Lancement du frontend Next.js...
start "CourseScope Frontend" /D "%FRONTEND_DIR%" cmd /k "set NEXT_PUBLIC_API_URL=http://localhost:8000 && %PM% install && %PM% run dev"

echo [INFO] Ouverture du navigateur...
start "" http://localhost:3000

echo.
echo [INFO] Deux fenetres ont ete ouvertes (API + Frontend).
echo [INFO] Fermez-les pour arreter l'application.

endlocal
exit /b 0

:fail
echo.
echo [ERREUR] Le script s'est arrete. Voir les messages ci-dessus.
pause
endlocal
exit /b 1
