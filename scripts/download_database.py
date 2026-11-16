"""Download en pak de NIST IR-spectra uit (NistChemData).

Gebruik:
    python scripts/download_database.py

Wat dit script doet:
1. Downloadt het archief ``nist_IR.zip`` (ongeveer 200 MB).
2. Controleert met een SHA-256-controlegetal dat het bestand compleet en
   ongewijzigd is.
3. Pakt alle JCAMP-DX-bestanden (.jdx) veilig uit naar ``data/raw/nist_ir/``.

Over de bron (belangrijk, zie ook README en docs/ethiek_en_verantwoord_gebruik.md):
- De spectra komen uit het NIST Chemistry WebBook (NIST Standard Reference
  Database 69) en zijn verzameld in de ONOFFICIELE repository NistChemData van
  Ivan Chernyshov.
- De oorspronkelijke repository (nu github.com/muCommons/NistChemData) heeft de
  databestanden in mei 2026 verwijderd. Het archief staat nog wel in oudere
  forks van die repository; daar halen we het vandaan. Het controlegetal
  hieronder komt uit de Git-LFS-verwijzing van de oorspronkelijke repository,
  dus we weten zeker dat het hetzelfde bestand is.
- De data is alleen voor lokaal gebruik (onderwijs) en wordt niet meegeleverd in
  deze repository.

Dit script gebruikt alleen de standaardbibliotheek van Python.
"""

from __future__ import annotations

import hashlib
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# --- Instellingen -----------------------------------------------------------

# Twee forks die het oude archief nog hebben; de tweede is reserve.
BRON_URLS = [
    "https://media.githubusercontent.com/media/glsalierno/NistChemData/main/data/spectra/raw/nist_IR.zip",
    "https://media.githubusercontent.com/media/jaythawmeee/NistChemData/main/data/spectra/raw/nist_IR.zip",
]

# Gegevens uit de Git-LFS-verwijzing van het originele bestand.
VERWACHTE_SHA256 = "38b4a14116182e8914dbe475638675c4015e691b9146d26f5ff3427b7b299270"
VERWACHTE_GROOTTE = 202_550_662  # bytes

PROJECTMAP = Path(__file__).resolve().parent.parent
RAW_MAP = PROJECTMAP / "data" / "raw"
ZIP_PAD = RAW_MAP / "nist_IR.zip"
UITPAK_MAP = RAW_MAP / "nist_ir"
KLAAR_MARKERING = UITPAK_MAP / "_uitpakken_klaar.txt"

# Beveiliging tegen "zip-bommen": we pakken nooit meer uit dan dit.
MAX_UITGEPAKT_TOTAAL = 4 * 1024**3  # 4 GB
MAX_UITGEPAKT_PER_BESTAND = 50 * 1024**2  # 50 MB


# --- Hulpfuncties -----------------------------------------------------------

def sha256_van_bestand(pad: Path) -> str:
    """Bereken het SHA-256-controlegetal van een bestand (in blokken, zuinig met geheugen)."""
    h = hashlib.sha256()
    with open(pad, "rb") as f:
        for blok in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


def zip_is_al_goed() -> bool:
    """True als het zip-bestand al aanwezig is en het controlegetal klopt."""
    if not ZIP_PAD.exists() or ZIP_PAD.stat().st_size != VERWACHTE_GROOTTE:
        return False
    return sha256_van_bestand(ZIP_PAD) == VERWACHTE_SHA256


def download(url: str, doel: Path) -> None:
    """Download ``url`` naar ``doel`` en toon de voortgang."""
    tijdelijk = doel.with_suffix(".zip.tmp")
    verzoek = urllib.request.Request(url, headers={"User-Agent": "ir-stofherkenner-setup"})
    start = time.time()
    with urllib.request.urlopen(verzoek, timeout=60) as antwoord, open(tijdelijk, "wb") as f:
        totaal = int(antwoord.headers.get("Content-Length") or 0)
        binnen = 0
        volgende_melding = 0.0
        while True:
            blok = antwoord.read(1024 * 256)
            if not blok:
                break
            f.write(blok)
            binnen += len(blok)
            if time.time() >= volgende_melding:
                volgende_melding = time.time() + 5
                if totaal:
                    print(f"  {binnen / 1e6:7.1f} / {totaal / 1e6:.1f} MB ({100 * binnen / totaal:4.1f}%)", flush=True)
                else:
                    print(f"  {binnen / 1e6:7.1f} MB", flush=True)
    tijdelijk.replace(doel)
    print(f"  Download klaar in {time.time() - start:.0f} s.", flush=True)


def pak_veilig_uit(zip_pad: Path, doelmap: Path) -> int:
    """Pak alleen .jdx-bestanden uit, plat in ``doelmap``.

    Veiligheid: een zip-bestand kan bestandsnamen bevatten als ``../../iets``
    (het zogeheten "zip slip"-probleem). Daarom gebruiken we alleen de kale
    bestandsnaam, zonder mappen, en slaan we alles over wat geen .jdx is.
    """
    doelmap.mkdir(parents=True, exist_ok=True)
    aantal = 0
    totaal_bytes = 0
    with zipfile.ZipFile(zip_pad) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            naam = Path(info.filename.replace("\\", "/")).name  # alleen de bestandsnaam
            if not naam.lower().endswith((".jdx", ".dx")):
                continue
            if info.file_size > MAX_UITGEPAKT_PER_BESTAND:
                print(f"  Overgeslagen (te groot): {naam}")
                continue
            totaal_bytes += info.file_size
            if totaal_bytes > MAX_UITGEPAKT_TOTAAL:
                raise RuntimeError("Het archief is uitgepakt onverwacht groot; uitpakken gestopt.")
            with z.open(info) as bron, open(doelmap / naam, "wb") as doel:
                doel.write(bron.read())
            aantal += 1
            if aantal % 2000 == 0:
                print(f"  {aantal} bestanden uitgepakt...", flush=True)
    return aantal


# --- Hoofdprogramma ---------------------------------------------------------

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows-console: speciale tekens niet laten crashen
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    RAW_MAP.mkdir(parents=True, exist_ok=True)

    # Stap 1: downloaden (alleen als het nog niet goed aanwezig is)
    if zip_is_al_goed():
        print("Het archief is al gedownload en het controlegetal klopt.")
    else:
        gelukt = False
        for url in BRON_URLS:
            print(f"Downloaden van:\n  {url}")
            try:
                download(url, ZIP_PAD)
            except (urllib.error.URLError, OSError, TimeoutError) as fout:
                print(f"  Mislukt: {fout}")
                continue
            print("Controlegetal (SHA-256) controleren...")
            if zip_is_al_goed():
                print("  Controlegetal klopt.")
                gelukt = True
                break
            print("  Controlegetal klopt NIET; bestand wordt verwijderd.")
            ZIP_PAD.unlink(missing_ok=True)
        if not gelukt:
            print(
                "\nFOUT: de database kon niet worden gedownload.\n"
                "Controleer je internetverbinding en probeer het opnieuw. Als het dan nog\n"
                "niet lukt, zijn de bronbestanden mogelijk offline gehaald.",
                file=sys.stderr,
            )
            return 1

    # Stap 2: uitpakken (alleen als dat nog niet gedaan is)
    if KLAAR_MARKERING.exists():
        print(f"De spectra zijn al uitgepakt in {UITPAK_MAP}")
        return 0
    print(f"Uitpakken naar {UITPAK_MAP} ...")
    aantal = pak_veilig_uit(ZIP_PAD, UITPAK_MAP)
    KLAAR_MARKERING.write_text(f"{aantal} bestanden uitgepakt\n", encoding="utf-8")
    print(f"Klaar: {aantal} JCAMP-DX-bestanden uitgepakt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
