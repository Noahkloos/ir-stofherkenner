"""Vergelijk voorbewerkingsvarianten voor de matching (onderbouwing ontwerpkeuze).

Gebruik:
    python scripts/vergelijk_voorbewerking.py

Vraag: moeten we de kale absorbantie vergelijken, of eerst iets met het
spectrum doen? We testen twee ideeen, los en gecombineerd:

- COMPRESSIE van de piekhoogtes (wortel, derdemachtswortel, logaritme), zodat
  zwakke pieken zwaarder meetellen;
- de EERSTE AFGELEIDE (helling), zodat de basislijn wegvalt.

Om niet "af te stellen op de testset" zijn de stoffen vast in twee helften
verdeeld. Alle varianten worden vergeleken op de AFSTELHELFT. Daarna wordt
alleen de gekozen variant (en de uitgangssituatie) nagerekend op de
CONTROLEHELFT, die bij het kiezen niet is gebruikt.

Uitvoer: docs/vergelijking_voorbewerking.md en docs/vergelijking_voorbewerking.csv
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECTMAP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECTMAP))
sys.path.insert(0, str(PROJECTMAP / "scripts"))

from evaluatie import evalueer_methode, helft_van_stof  # noqa: E402
from stofherkenner.matching import laad_bibliotheek, maak_bibliotheek  # noqa: E402
from stofherkenner.voorbewerking import AFGELEIDE_VENSTER, COMPRESSIE, vergelijkingsvorm  # noqa: E402

DOCS = PROJECTMAP / "docs"

# (naam, compressie, venster voor de afgeleide; 0 = geen afgeleide)
VARIANTEN = [
    ("kale absorbantie (uitgangssituatie)", "geen", 0),
    ("alleen wortel", "wortel", 0),
    ("alleen logaritme", "log", 0),
    ("alleen afgeleide", "geen", 9),
    ("wortel + afgeleide", "wortel", 9),
    ("derdemachtswortel + afgeleide", "derdemachtswortel", 9),
    ("logaritme + afgeleide (venster 9)", "log", 9),
    ("logaritme + afgeleide (venster 5)", "log", 5),
    ("logaritme + afgeleide (venster 13)", "log", 13),
]
RUISNIVEAUS = (0.01, 0.03)      # extra ruis als fractie van de hoogste piek


def voeg_ruis_toe(absorbantie: np.ndarray, maskers: np.ndarray, sigma: float, rng) -> np.ndarray:
    """Tel willekeurige ruis op bij genormaliseerde spectra en normaliseer opnieuw."""
    m = maskers > 0
    a = absorbantie.astype(float) + rng.normal(0.0, sigma, absorbantie.shape)
    a = np.where(m, a, np.inf)
    a = a - a.min(axis=1, keepdims=True)            # basislijn weer op 0
    a = np.where(m, a, 0.0)
    return a / a.max(axis=1, keepdims=True)          # hoogste piek weer op 1


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows-console: speciale tekens niet laten crashen
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    start = time.time()
    basis = laad_bibliotheek(PROJECTMAP / "data", alleen_uniek=True)
    meta = basis.metadata
    stof_nummer = pd.factorize(meta["nist_id"])[0]
    aantal_per_stof = np.bincount(stof_nummer)
    helft = np.array([helft_van_stof(s) for s in meta["nist_id"]])
    testbaar = aantal_per_stof[stof_nummer] >= 2
    afstel = np.flatnonzero(testbaar & (helft == 0))
    controle = np.flatnonzero(testbaar & (helft == 1))
    print(f"Afstelhelft: {len(afstel)} spectra, controlehelft: {len(controle)} spectra")

    def meet(compressie: str, venster: int, vragen: np.ndarray, sigma: float = 0.0) -> tuple[float, float]:
        """Top-1 en top-5 (cosinus) voor een variant op de gegeven vraagspectra."""
        bib = maak_bibliotheek(basis.absorbantie, basis.maskers, meta, basis.raster,
                               compressie=compressie, afgeleide_venster=venster)
        vraag_vectoren = None
        if sigma > 0:
            rng = np.random.default_rng(1)       # vaste "seed": elke run geeft dezelfde ruis
            met_ruis = voeg_ruis_toe(basis.absorbantie[vragen], basis.maskers[vragen], sigma, rng)
            vraag_vectoren = vergelijkingsvorm(met_ruis, basis.maskers[vragen] > 0,
                                               compressie=compressie, afgeleide_venster=venster)
        rang = evalueer_methode(bib, vragen, stof_nummer, "cosinus", vraag_vectoren)["rang"]
        return float((rang == 1).mean()), float((rang <= 5).mean())

    rijen = []
    for naam, compressie, venster in VARIANTEN:
        top1, top5 = meet(compressie, venster, afstel)
        rij = {"variant": naam, "compressie": compressie, "venster": venster, "top1": top1, "top5": top5}
        for sigma in RUISNIVEAUS:
            rij[f"top1_ruis_{sigma}"], rij[f"top5_ruis_{sigma}"] = meet(compressie, venster, afstel, sigma)
        rijen.append(rij)
        print(f"{naam:38s} top-1 {100 * top1:5.1f}%  top-5 {100 * top5:5.1f}%  "
              + "  ".join(f"ruis {s}: {100 * rij[f'top1_ruis_{s}']:.1f}%" for s in RUISNIVEAUS), flush=True)
    tabel = pd.DataFrame(rijen)

    # Controlehelft: alleen de uitgangssituatie en de gekozen instelling uit voorbewerking.py
    controle_basis = meet("geen", 0, controle)
    controle_gekozen = meet(COMPRESSIE, AFGELEIDE_VENSTER, controle)
    afstel_gekozen = meet(COMPRESSIE, AFGELEIDE_VENSTER, afstel)
    afstel_basis = meet("geen", 0, afstel)
    print(f"Controlehelft: uitgangssituatie top-1 {100 * controle_basis[0]:.1f}%, gekozen top-1 {100 * controle_gekozen[0]:.1f}%")

    DOCS.mkdir(exist_ok=True)
    tabel.round(4).to_csv(DOCS / "vergelijking_voorbewerking.csv", index=False, encoding="utf-8")

    def p(x: float) -> str:
        return f"{100 * x:.1f}%"

    tabel_md = "\n".join(
        f"| {r['variant']} | {p(r['top1'])} | {p(r['top5'])} | "
        + " | ".join(p(r[f"top1_ruis_{s}"]) for s in RUISNIVEAUS) + " |"
        for r in rijen
    )
    rapport = f"""# Vergelijking van voorbewerkingsvarianten voor de matching

> Automatisch gemaakt door `scripts/vergelijk_voorbewerking.py` op {date.today().isoformat()}.
> Alle getallen komen uit een echte run. Opnieuw draaien: `.venv\\Scripts\\python scripts\\vergelijk_voorbewerking.py`

## Waarom dit onderzoek?

De eerste versie van de matching vergeleek de kale, genormaliseerde absorbantie. Dat gaf een teleurstellende
top-1-nauwkeurigheid. Twee bekende zwakke punten van die aanpak:

1. **De hoogste piek domineert.** Piekhoogtes hangen af van concentratie, laagdikte en fase; piekposities veel minder.
   Oplossing: de hoogtes samendrukken (*compressie*), zodat zwakke pieken zwaarder meetellen.
2. **De basislijn telt mee.** Vaste stoffen en oude metingen hebben vaak een scheve of verhoogde basislijn.
   Oplossing: de *eerste afgeleide* (helling) vergelijken; een langzaam verlopende basislijn heeft bijna geen helling.

## Opzet

- Zelfde leave-one-out-test als in [evaluatie.md](evaluatie.md), met cosinusgelijkenis.
- De stoffen zijn vast in twee helften verdeeld. **Alle varianten zijn alleen op de afstelhelft vergeleken**
  ({len(afstel)} testspectra). De controlehelft ({len(controle)} testspectra) is pas daarna gebruikt, en alleen voor de gekozen variant.
- Ruistest: bij het testspectrum is willekeurige ruis opgeteld (standaarddeviatie 1% en 3% van de hoogste piek)
  om te zien of een variant niet alleen op "schone" NIST-spectra werkt.

## Resultaten op de afstelhelft (cosinus)

| Variant | Top-1 | Top-5 | Top-1 met 1% ruis | Top-1 met 3% ruis |
|---|---|---|---|---|
{tabel_md}

## Keuze

Gekozen instelling in `stofherkenner/voorbewerking.py`: **compressie = `{COMPRESSIE}`, afgeleide met venster {AFGELEIDE_VENSTER}**.

## Bevestiging op de controlehelft

| | Afstelhelft top-1 / top-5 | Controlehelft top-1 / top-5 |
|---|---|---|
| Kale absorbantie (uitgangssituatie) | {p(afstel_basis[0])} / {p(afstel_basis[1])} | {p(controle_basis[0])} / {p(controle_basis[1])} |
| Gekozen instelling | {p(afstel_gekozen[0])} / {p(afstel_gekozen[1])} | {p(controle_gekozen[0])} / {p(controle_gekozen[1])} |

De controlehelft is niet gebruikt bij het kiezen. Als de winst daar ongeveer even groot is als op de afstelhelft,
is de verbetering echt en geen toeval of overfitting.

## Kanttekeningen

- Er is bewust maar een klein aantal varianten geprobeerd. Hoe meer varianten je op dezelfde data probeert, hoe
  groter de kans dat de beste "toevallig" goed scoort.
- De ruistest gebruikt kunstmatige, gelijkmatige ruis. Echte meetfouten (waterdamp, CO₂, ATR-effecten) zijn
  anders van aard en zijn hier niet getest.
- Logaritmische compressie maakt de score gevoeliger voor kleine piekjes. Bij een erg ruizig spectrum kan dat
  nadelig zijn; de ruistest hierboven laat zien hoeveel de nauwkeurigheid dan daalt.

Rekentijd: {time.time() - start:.0f} s.
"""
    (DOCS / "vergelijking_voorbewerking.md").write_text(rapport, encoding="utf-8")
    print(f"Rapport geschreven naar {DOCS / 'vergelijking_voorbewerking.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
