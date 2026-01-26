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

echo [INFO] Lancement de l'application Streamlit...
python -m streamlit run CourseScope.py

echo.
echo [INFO] Fin de l'application. Appuie sur une touche pour fermer.
pause

endlocal
exit /b 0

:fail
echo.
echo [ERREUR] Le script s'est arrete. Voir les messages ci-dessus.
pause
endlocal
exit /b 1
