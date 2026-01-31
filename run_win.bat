@echo off
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || goto :fail

set "VENV_DIR=%PROJECT_DIR%.venv"

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
    echo [INFO] Installation des dependances...
    pip install -r "%PROJECT_DIR%requirements.txt"
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
start "CourseScope API" cmd /k "cd /d \"%PROJECT_DIR%\" ^&^& call \"%VENV_DIR%\Scripts\activate.bat\" ^&^& python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000"

echo [INFO] Lancement du frontend Next.js (nouvelle stack)...
start "CourseScope Frontend" cmd /k "cd /d \"%PROJECT_DIR%frontend\" ^&^& if not exist node_modules (if exist package-lock.json (npm ci) else (npm install)) ^&^& npm run dev"

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
