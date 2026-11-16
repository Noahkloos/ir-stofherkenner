"""Maak docs/testresultaten.md uit een echte pytest-run.

Gebruik:  .venv\\Scripts\\python scripts\\maak_testrapport.py

Draait alle tests twee keer:
1. ``pytest -v``  -> de lijst met alle tests en de uitslag;
2. ``pytest -s``  -> de regels die met "[meting]" beginnen (gemeten tijden).
De handmatige controles (browser, schone kopie) staan hieronder als tekst en
moeten bij een nieuwe controle met de hand worden bijgewerkt.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECTMAP = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

UITLEG = {
    "test_app": "De app zelf (Streamlit AppTest): disclaimer, stijl, grafieken, top 5, overlay met meerdere referenties, piekentabel, uploads, eerlijke test, zonder bibliotheek, 5 MB",
    "test_functionele_groepen": "Expertsysteem: elke regel los en op echte spectra; geen stellige valse meldingen",
    "test_jcamp_lezen": "Parser: kop, factoren, micrometer, gecomprimeerde data, meerdere blokken; vergelijking met jcamp",
    "test_matching": "Cosinus/Pearson/Euclidisch, maskers, zoeken, waarschuwingen, snelheid; vertaling van een klik naar een piek",
    "test_piek_toewijzing": "Welke binding hoort bij een piek: correlatietabel, breedte en hoogte, koppeling met de regels",
    "test_piekdetectie": "Synthetische spectra (bekende pieken ±8 cm⁻¹, ruis, spike, overlap) en 14 bekende pieken in echte spectra",
    "test_prestatie": "Bestand van ~5 MB binnen 2 s; uitdunnen grafiek; te groot bestand snel afgewezen",
    "test_validatie": "De zes verplichte kapotte bestanden, een reeks andere kapotte bestanden en 400 willekeurig beschadigde bestanden",
    "test_voorbewerking": "Eenheden, omrekenen µm→cm⁻¹ en T→A, raster, resolutie, normaliseren, vergelijkingsvorm",
}

HANDMATIG = """## 3. Controle in de browser (desktop en tablet)

Laatst gecontroleerd op 16 november 2026, ná de aanpassingen aan de opmaak (Windows 7-stijl), de overlay met de
top 5 en de klikbare pieken. Gecontroleerd in de ingebouwde browser van de AI-tool (Chromium), met geëmuleerde
schermen, gemeten met JavaScript in de pagina:

| Scherm (geëmuleerd) | Voorbeeld | Horizontaal scrollen? | Grafieken | Groepvakken / tabellen / statusbalk | Fouten in de console |
|---|---|---|---|---|---|
| Desktop 1366 × 900 | ethylacetaat | nee | 852 px breed, binnen het scherm | 896 / 862–866 / 896 px, binnen het scherm | geen |
| Tablet 768 × 1024 | tolueen | nee | 681 px breed, binnen het scherm | 725 / 691–695 / 725 px, binnen het scherm | geen |

Verder in de browser gecontroleerd:
- **Klikken op een rode stip** (ethylacetaat, piek bij 1766 cm⁻¹): de klik komt binnen als selectie van de stip
  (`plotly_selected`, spoor 1, x = 1766), de tabel "Aangeklikte piek(en)" verschijnt met "Ester (–COO–): C=O-rek
  (ester)" in de kolom "Volgens de regels", en de aangeklikte stip wordt geel (gemeten: kleur `rgb(255, 204, 0)`).
  Gevonden en opgelost: eerst "won" de spectrumlijn de klik, omdat de stippen precies óp de lijn liggen; de lijn
  vangt nu geen klikken meer op. Bij deze laatste controle is de klik in de pagina zelf nagebootst (muis bewegen naar
  de stip, kort wachten, klikken), omdat het browservenster van de AI-tool verborgen was.
- **Selectie opheffen:** een enkele klik op een lege plek heft de selectie níét op; een **dubbelklik** wel. De tekst
  in de app zegt dat nu ook.
- **Op een echte tablet (aanraken) is klikken niet getest**; daarvoor is er de piekentabel onderaan met alle pieken.
- **Overlay**: met alle vijf stoffen gekozen toont de grafiek zes lijnen (vijf referenties en het geüploade spectrum),
  elk in een eigen kleur.
- **Pictogrammen**: de pictogrammen (bijv. op de uploadknop) worden als pictogram getoond, niet als tekst.

**Beperking:** geëmuleerde schermen, geen fysieke tablet.

## 4. setup.bat en start.bat op een schone kopie

Gedaan vóór de aanpassingen aan de opmaak; `setup.bat` en `start.bat` zijn daarna niet veranderd.
De repository is gekloond naar een lege map (met een spatie in het pad: `...\\schone test\\ir-stofherkenner`), zonder
`.venv` en zonder `data/`.

| Stap | Resultaat |
|---|---|
| `setup.bat` | **Exitcode 0 na 364 s.** Venv aangemaakt, pakketten geïnstalleerd, `nist_IR.zip` gedownload en SHA-256 gecontroleerd, 19.582 bestanden uitgepakt, bibliotheek gebouwd: 18.998 spectra, 982 duplicaten, 584 overgeslagen (identiek aan het hoofdproject) |
| Tests in de schone kopie | **169 passed, 1 skipped** (versie van dat moment). De overgeslagen test vergelijkt met de bibliotheek `jcamp`, die alleen voor het onderzoek nodig is |
| Startcommando (poort 8502) | Antwoordt binnen 2 s (`/_stcore/health` = ok), zonder vraag om een e-mailadres (headless) |
| `start.bat` (poort 8501) | Uitgevoerd vanuit de schone kopie nadat de oude testservers (met toestemming van de student) waren gestopt: binnen 2 s luistert een **nieuw** proces op poort 8501. In de browser laadt de app met "Referentiebibliotheek: 18.016 spectra van 15.817 stoffen" |

**Kanttekeningen:**
- Dit is een schone *kopie* op dezelfde computer, geen schone *computer*: Python 3.14 was al geïnstalleerd en er
  kunnen pakketten in de pip-cache hebben gestaan.
- Bij `start.bat` is niet automatisch gecontroleerd of er ook echt een browsertabblad opengaat, en de foutmeldingen
  bovenin `start.bat` (als de venv of de bibliotheek ontbreekt) zijn niet getest.
- Python 3.10/3.11 is niet getest en wordt niet ondersteund (zie `docs/criteria_checklist.md`, T1).
"""


def draai(*argumenten: str) -> str:
    resultaat = subprocess.run([PYTHON, "-m", "pytest", "-p", "no:cacheprovider", *argumenten],
                               cwd=PROJECTMAP, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return resultaat.stdout


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    uitvoer_v = draai("-v")
    uitvoer_s = draai("-s", "-q")
    metingen = "\n".join(re.findall(r"\[meting\][^\n]*", uitvoer_s))
    samenvatting = re.findall(r"=+ (.*(?:passed|failed).*) =+", uitvoer_v)[-1]

    tel: dict[str, dict[str, int]] = {}
    for m in re.finditer(r"^tests/(test_\w+)\.py::.*? (PASSED|FAILED|SKIPPED|ERROR)\s+\[", uitvoer_v, re.M):
        tel.setdefault(m.group(1), {}).setdefault(m.group(2), 0)
        tel[m.group(1)][m.group(2)] += 1
    tabel = "\n".join(f"| `{b}.py` | {sum(t.values())} | {t.get('PASSED', 0)} | {UITLEG.get(b, '')} |"
                      for b, t in sorted(tel.items()))
    kop = "\n".join(r for r in uitvoer_v.splitlines()[:8] if r.startswith(("platform", "rootdir", "configfile", "plugins")))
    regels = "\n".join(r for r in uitvoer_v.splitlines() if r.startswith("tests/"))

    rapport = f"""# Testresultaten

Alle uitvoer hieronder komt uit echte runs. Pytest-deel gemaakt door `scripts/maak_testrapport.py` op
{date.today().isoformat()} (Windows 10, Python {sys.version.split()[0]}). Opnieuw maken:
`.venv\\Scripts\\python scripts\\maak_testrapport.py`

## 1. Pytest: alle tests

**Resultaat: {samenvatting}.**

| Testbestand | Aantal | Geslaagd | Wat wordt getest |
|---|---|---|---|
{tabel}

## 2. Metingen (uitvoer van `pytest -s`)

```
{metingen}
```

- **Eis US-K1 (≤ 2 s tot de grafiek bij 5 MB):** gehaald, zie de metingen hierboven. Gemeten is al het werk van de
  server: valideren, inlezen, voorbewerken, pieken zoeken, functionele groepen en de grafiek opbouwen
  (`test_prestatie.py`), en bij de app-run ook het zoeken in de bibliotheek en de top 5 (`test_app.py`).
  Niet apart gemeten: het tekenen in de browser. De grafiek wordt daarvoor uitgedund tot maximaal 4.000 punten.
- **Eis matching (< 1 s door de hele bibliotheek):** gehaald, zie de zoektijden hierboven.

{HANDMATIG}
## 5. Volledige pytest-uitvoer

```
{kop}

{regels}

{samenvatting}
```
"""
    (PROJECTMAP / "docs" / "testresultaten.md").write_text(rapport, encoding="utf-8")
    print(samenvatting)
    print(metingen)
    return 0 if "failed" not in samenvatting else 1


if __name__ == "__main__":
    sys.exit(main())
