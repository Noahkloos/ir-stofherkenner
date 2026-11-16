@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  IR-Stofherkenner - installatie
echo  Dit duurt ongeveer 5 tot 10 minuten (download van 200 MB).
echo ============================================================
echo.

rem --- Stap 1: zoek een geschikte Python (3.12 of hoger) ---
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto python_gevonden
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto python_gevonden
echo FOUT: er is geen Python 3.12 of hoger gevonden.
echo Installeer Python via https://www.python.org/downloads/ en vink bij het
echo installeren "Add python.exe to PATH" aan. Start daarna setup.bat opnieuw.
goto fout

:python_gevonden
echo [1/4] Python gevonden:
%PY% --version

rem --- Stap 2: virtual environment en pakketten ---
if exist ".venv\Scripts\python.exe" goto venv_bestaat
echo [2/4] Virtual environment aanmaken in de map .venv ...
%PY% -m venv .venv
if errorlevel 1 goto fout
:venv_bestaat
echo [2/4] Pakketten installeren (requirements-dev.txt) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt --quiet
if errorlevel 1 goto fout

rem --- Stap 3: database downloaden ---
echo [3/4] NIST IR-database downloaden en uitpakken ...
".venv\Scripts\python.exe" scripts\download_database.py
if errorlevel 1 goto fout

rem --- Stap 4: bibliotheek bouwen ---
echo [4/4] Referentiebibliotheek bouwen (ongeveer 1 tot 2 minuten) ...
".venv\Scripts\python.exe" scripts\build_library.py
if errorlevel 1 goto fout

echo.
echo ============================================================
echo  Klaar! Dubbelklik op start.bat om de app te starten.
echo ============================================================
pause
exit /b 0

:fout
echo.
echo ============================================================
echo  De installatie is NIET gelukt. Lees de melding hierboven.
echo ============================================================
pause
exit /b 1
