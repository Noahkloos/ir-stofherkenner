"""Structuurformules van de stoffen in de top 5.

De NIST-spectrumbestanden bevatten geen structuur, alleen naam, CAS-nummer en
molecuulformule. De structuur halen we daarom bij dezelfde bron op: het NIST
Chemistry WebBook levert per stof een 2D-structuurbestand (een "molfile").

Werkwijze:
1. Is de structuur al eerder opgehaald? Dan staat hij in ``data/structuren/``
   (de cache) en hoeft er niets van internet.
2. Zo niet, en ophalen mag (instelling in de app), dan vragen we bij NIST het
   bestand op voor het NIST-ID van de stof (bijv. C67641 voor aceton). Er wordt
   alleen dat ID verstuurd, nooit het spectrum van de gebruiker.
3. Het bestand wordt gecontroleerd (is het echt een molfile met atomen?) en pas
   dan in de cache gezet. Een foutpagina wordt nooit bewaard.
4. RDKit tekent de structuurformule als SVG-afbeelding.

Lukt iets niet (geen internet, onbekende stof, RDKit ontbreekt), dan geeft de
functie ``None`` terug en toont de app "geen structuur beschikbaar". De app
crasht er nooit op.

Bron en rechten: NIST Chemistry WebBook (NIST SRD 69), © U.S. Secretary of
Commerce. De opgehaalde bestanden blijven lokaal en komen niet in git.
"""

from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

NIST_URL = "https://webbook.nist.gov/cgi/cbook.cgi?Str2File={nist_id}"
TIMEOUT_SECONDEN = 6
PAUZE_TUSSEN_VERZOEKEN = 0.5        # beleefd blijven tegenover de NIST-server
OPNIEUW_PROBEREN_NA = 300           # na een netwerkfout 5 minuten niet opnieuw proberen
GELDIG_ID = re.compile(r"^[BC]\d{3,12}$")   # NIST-ID's: C67641, B6000033, ...
GEEN_STRUCTUUR = "GEEN_STRUCTUUR\n"  # inhoud van een cachebestand als NIST zegt: er is geen structuur

# Met IR_STOFHERKENNER_OFFLINE=1 gaat er nooit iets naar internet (gebruikt door de tests).
OFFLINE = os.environ.get("IR_STOFHERKENNER_OFFLINE") == "1"

_mislukt: dict[str, float] = {}     # NIST-ID -> tijdstip van de laatste netwerkfout (geheugen van deze sessie)
_laatste_verzoek = 0.0

try:                                 # RDKit is nodig om te tekenen; zonder RDKit werkt de rest van de app gewoon
    from rdkit import Chem, RDLogger
    from rdkit.Chem.Draw import rdMolDraw2D
    RDLogger.DisableLog("rdApp.*")   # geen waarschuwingen van RDKit in het zwarte venster
    RDKIT_BESCHIKBAAR = True
except ImportError:                  # pragma: no cover - alleen als rdkit niet geinstalleerd is
    RDKIT_BESCHIKBAAR = False


def is_geldig_id(nist_id: str) -> bool:
    """Alleen echte NIST-ID's mogen in een URL of bestandsnaam terechtkomen."""
    return bool(GELDIG_ID.match(nist_id or ""))


def aantal_atomen(molblock: str) -> int:
    """Lees het aantal atomen uit de 'counts'-regel (regel 4) van een V2000-molfile; -1 als het geen molfile is."""
    regels = molblock.splitlines()
    if len(regels) < 4 or "V2000" not in regels[3] or "M  END" not in molblock:
        return -1
    try:
        return int(regels[3][:3])
    except ValueError:
        return -1


def _cachebestand(cachemap: Path, nist_id: str) -> Path:
    return cachemap / f"{nist_id}.mol"


def normaliseer_regeleindes(tekst: str) -> str:
    """Zet alle regeleindes om naar "\\n".

    NIST levert molfiles met Windows-regeleindes ("\\r\\n"). Zonder deze stap kwam
    er bij opslaan op Windows een extra "\\r" bij, en dan kon RDKit het bestand uit
    de cache niet meer lezen (gevonden bij het testen in de browser). Ook al
    beschadigde bestanden ("\\r\\r\\n") worden hiermee weer goed.
    """
    return re.sub(r"\r+\n", "\n", tekst).replace("\r", "\n")


def _lees_cache(pad: Path) -> str:
    return normaliseer_regeleindes(pad.read_bytes().decode("latin-1"))


def _schrijf_cache(pad: Path, tekst: str) -> None:
    pad.write_bytes(normaliseer_regeleindes(tekst).encode("latin-1"))   # bytes: Windows voegt dan niets toe


def _download(nist_id: str) -> str | None:
    """Haal het molfile op bij NIST. Geeft de tekst terug, of None bij een netwerkfout."""
    global _laatste_verzoek
    wacht = PAUZE_TUSSEN_VERZOEKEN - (time.time() - _laatste_verzoek)
    if wacht > 0:
        time.sleep(wacht)
    verzoek = urllib.request.Request(NIST_URL.format(nist_id=nist_id), headers={"User-Agent": "ir-stofherkenner (onderwijs)"})
    try:
        with urllib.request.urlopen(verzoek, timeout=TIMEOUT_SECONDEN) as antwoord:
            tekst = antwoord.read(200_000).decode("latin-1")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return None
    finally:
        _laatste_verzoek = time.time()
    return tekst


def haal_molfile(nist_id: str, cachemap: Path, online: bool = True) -> str | None:
    """Geef het molfile van een stof, uit de cache of (als dat mag) van NIST.

    Geeft None als er geen structuur is of als hij nu niet op te halen is.
    """
    if not is_geldig_id(nist_id):
        return None
    pad = _cachebestand(cachemap, nist_id)
    if pad.exists():
        inhoud = _lees_cache(pad)
        return None if inhoud == GEEN_STRUCTUUR else inhoud

    if not online or OFFLINE:
        return None
    if time.time() - _mislukt.get(nist_id, 0.0) < OPNIEUW_PROBEREN_NA:
        return None                                  # kort geleden mislukt: niet steeds opnieuw wachten

    tekst = _download(nist_id)
    if tekst is None:
        _mislukt[nist_id] = time.time()
        return None
    tekst = normaliseer_regeleindes(tekst)
    atomen = aantal_atomen(tekst)
    if atomen < 0:                                   # geen molfile (bijv. een foutpagina): niet bewaren
        _mislukt[nist_id] = time.time()
        return None
    cachemap.mkdir(parents=True, exist_ok=True)
    if atomen == 0:                                  # NIST zegt: geen structuur bekend. Dat onthouden we.
        _schrijf_cache(pad, GEEN_STRUCTUUR)
        return None
    _schrijf_cache(pad, tekst)
    return tekst


def teken_svg(molblock: str, breedte: int = 220, hoogte: int = 160) -> str | None:
    """Teken een structuurformule als SVG (zwart-wit, zoals in een studieboek). None als dat niet lukt."""
    if not RDKIT_BESCHIKBAAR or not molblock:
        return None
    try:
        mol = Chem.MolFromMolBlock(molblock, sanitize=True, removeHs=True)
        if mol is None:                              # soms keurt RDKit een NIST-bestand af; probeer het soepeler
            mol = Chem.MolFromMolBlock(molblock, sanitize=False, removeHs=False)
        if mol is None or mol.GetNumAtoms() == 0:
            return None
        tekenaar = rdMolDraw2D.MolDraw2DSVG(breedte, hoogte)
        opties = tekenaar.drawOptions()
        opties.clearBackground = False               # doorzichtige achtergrond
        opties.useBWAtomPalette()                    # zwart-wit
        opties.bondLineWidth = 1.5
        opties.padding = 0.08
        tekenaar.DrawMolecule(mol)
        tekenaar.FinishDrawing()
        svg = tekenaar.GetDrawingText()
        return svg[svg.find("<svg"):]                # zonder de XML-kopregel
    except Exception:                                # tekenen mag de app nooit laten crashen
        return None


def structuur_svg(nist_id: str, cachemap: Path, online: bool = True) -> str | None:
    """Molfile ophalen (cache of NIST) en tekenen. None als er geen structuur te tonen is."""
    molblock = haal_molfile(nist_id, cachemap, online)
    return teken_svg(molblock) if molblock else None
