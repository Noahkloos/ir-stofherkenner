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
echo De app opent vanzelf in je browser op http://localhost:8501
echo Laat dit venster open zolang je de app gebruikt. Sluiten = app stoppen.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
pause
