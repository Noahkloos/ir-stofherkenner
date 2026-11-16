"""De referentiebibliotheek automatisch opzetten (voor gebruik op een server, zoals Streamlit Cloud).

Op een eigen laptop doet ``setup.bat`` dit. Op Streamlit Cloud bestaat er geen
setup.bat: de app wordt daar rechtstreeks vanaf GitHub gestart, en de NIST-data
staat bewust NIET op GitHub. Daarom bouwt de app de bibliotheek daar zelf, bij de
eerste start:

1. ``scripts/download_database.py --niet-uitpakken``: download het NIST-archief
   (~200 MB) en controleer het SHA-256-controlegetal;
2. ``scripts/build_library.py``: bouw de bibliotheek rechtstreeks uit de zip;
3. ruim de zip daarna op (scheelt ~200 MB schijfruimte).

Dat gebeurt alleen als ``moet_automatisch_bouwen()`` ja zegt: op Streamlit Cloud
(de app staat dan in /mount/src/...) of als de omgevingsvariabele
``IR_STOFHERKENNER_AUTOBOUW=1`` is gezet. Lokaal (en in de tests) gebeurt het niet
vanzelf; daar is setup.bat voor.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

# Maar één bouwproces tegelijk, ook als meerdere bezoekers de app tegelijk openen.
# (Deze module wordt één keer per serverproces geladen, dus het slot is gedeeld.)
BOUWSLOT = threading.Lock()


def moet_automatisch_bouwen(projectmap: Path) -> bool:
    """True op Streamlit Cloud of als IR_STOFHERKENNER_AUTOBOUW=1."""
    if os.environ.get("IR_STOFHERKENNER_AUTOBOUW") == "1":
        return True
    if os.environ.get("IR_STOFHERKENNER_AUTOBOUW") == "0":
        return False
    return projectmap.resolve().as_posix().startswith("/mount/src/")


def _draai(script: Path, argumenten: list[str], melding: Callable[[str], None]) -> int:
    """Draai een script en geef elke regel uitvoer door aan ``melding``. Geeft de exitcode terug."""
    proces = subprocess.Popen(
        [sys.executable, "-u", str(script), *argumenten],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    assert proces.stdout is not None
    for regel in proces.stdout:
        regel = regel.rstrip()
        if regel:
            melding(regel)
    return proces.wait()


def bouw_bibliotheek(projectmap: Path, melding: Callable[[str], None] = print) -> bool:
    """Download het archief en bouw de bibliotheek. True als het gelukt is."""
    scripts = projectmap / "scripts"
    melding("Stap 1 van 2: NIST-archief downloaden (± 200 MB) en controleren...")
    if _draai(scripts / "download_database.py", ["--niet-uitpakken"], melding) != 0:
        melding("Downloaden mislukt.")
        return False
    melding("Stap 2 van 2: referentiebibliotheek bouwen (± 1–3 minuten)...")
    if _draai(scripts / "build_library.py", [], melding) != 0:
        melding("Bouwen mislukt.")
        return False
    zip_pad = projectmap / "data" / "raw" / "nist_IR.zip"
    try:
        zip_pad.unlink(missing_ok=True)                 # opruimen: de bibliotheek is nu klaar
    except OSError:
        pass
    melding("Klaar: de referentiebibliotheek is gebouwd.")
    return (projectmap / "data" / "library.npz").exists()
