@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo De app is nog niet geinstalleerd. Dubbelklik eerst op setup.bat.
    pause
    exit /b 1
)
if not exist "data\library.npz" (
    echo De referentiebibliotheek ontbreekt. Dubbelklik eerst op setup.bat.
    pause
    exit /b 1
)

echo IR-Stofherkenner wordt gestart...
echo De app opent over een paar seconden vanzelf in je browser: http://localhost:8501
echo Gebeurt dat niet? Typ dat adres zelf in je browser.
echo Laat dit venster open zolang je de app gebruikt. Sluiten = app stoppen.
echo.
rem Browser openen na 5 seconden (dan is de server klaar), in een apart proces
start "" /min cmd /c "timeout /t 5 /nobreak >nul & start "" http://localhost:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
pause
