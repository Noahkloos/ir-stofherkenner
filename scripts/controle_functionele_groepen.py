"""Toets de functionele-groepenregels op de hele NIST-bibliotheek.

Gebruik:
    python scripts/controle_functionele_groepen.py

De bibliotheek bevat geen lijstje "deze stof heeft groep X". Daarom gebruiken we
twee dingen die we WEL weten:

1. De NAAM. Een stof die "...nitrile" heet heeft een nitrilgroep, "...ol" is
   (meestal) een alcohol, enzovoort. Voor zulke stoffen hoort de regel af te
   gaan. Hoe vaak dat gebeurt noemen we de TREFKANS (sensitiviteit).
   Let op: naamherkenning is grof (niet elke alcohol heet "...ol"), dus dit is
   een indicatie, geen exacte meting.

2. De MOLECUULFORMULE. Zonder stikstof kan er geen amine of nitril zijn; zonder
   zuurstof geen alcohol, keton, ester of zuur; een verzadigde stof (CnH2n+2,
   eventueel met O) kan geen C=C, C=O of benzeenring hebben. Gaat een regel
   daar toch af, dan is dat ZEKER een vals alarm. Dat percentage is wel exact.

Uitvoer: docs/controle_functionele_groepen.md en .csv
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECTMAP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECTMAP))
sys.path.insert(0, str(PROJECTMAP / "scripts"))

from evaluatie import formule_naar_telling  # noqa: E402
from stofherkenner.functionele_groepen import herken_functionele_groepen  # noqa: E402
from stofherkenner.matching import laad_bibliotheek  # noqa: E402
from stofherkenner.piekdetectie import detecteer_pieken  # noqa: E402

DOCS = PROJECTMAP / "docs"


def verzadigd(f: dict[str, int]) -> bool:
    """True voor CnH2n+2 (eventueel met O): geen dubbele bindingen of ringen mogelijk."""
    return bool(f) and set(f) <= {"C", "H", "O"} and f.get("C", 0) >= 1 and f.get("H", 0) == 2 * f.get("C", 0) + 2


# Per groep: (naam van de bevinding, naam-patroon voor "hoort aanwezig te zijn",
#             functie op de formule die True geeft als de groep ONMOGELIJK is, uitleg daarvan)
GROEPEN = [
    ("O–H (alcohol of fenol)",
     lambda n: bool(re.search(r"(?<!thi)ol\b|alcohol|phenol", n)) and "thiol" not in n and "ester" not in n,
     lambda f: f.get("O", 0) == 0, "geen zuurstof in de formule"),
    ("Carbonzuur (–COOH)",
     lambda n: bool(re.search(r"\bacid\b", n)) and not re.search(r"ester|anhydride|amide|salt|sulf|phosph|bor|chloride|nitrile|hydrazide", n),
     lambda f: f.get("O", 0) < 2, "minder dan twee zuurstofatomen"),
    ("C=O (keton of aldehyde)",
     lambda n: bool(re.search(r"one\b|aldehyde|ketone|\w{3,}anal\b", n)) and not re.search(r"sulfone|lactone|silicone|oxime|hydrazone", n),
     lambda f: f.get("O", 0) == 0 or verzadigd(f), "geen zuurstof, of verzadigd (CnH2n+2)"),
    ("Ester (–COO–)",
     lambda n: bool(re.search(r"\bester\b|acetate|benzoate|formate|propionate|propanoate|butyrate|butanoate|oate\b|phthalate|acrylate", n))
     and not re.search(r"phosph|sulf|nitr|bor|silic|carbam|thio|carbon", n),
     lambda f: f.get("O", 0) < 2 or verzadigd(f), "minder dan twee zuurstofatomen, of verzadigd"),
    ("N–H (amine)",
     lambda n: bool(re.search(r"amine\b|aniline\b", n)),
     lambda f: f.get("N", 0) == 0, "geen stikstof in de formule"),
    ("C≡N (nitril)",
     lambda n: bool(re.search(r"nitrile\b|cyanide\b", n)) and "isocyan" not in n,
     lambda f: f.get("N", 0) == 0, "geen stikstof in de formule"),
    ("C=C (alkeen)",
     lambda n: bool(re.search(r"(eth|prop|but|pent|hex|hept|oct|non|dec)a?(di|tri)?ene\b|ethylene|propylene|vinyl|allyl", n)),
     lambda f: verzadigd(f), "verzadigd (CnH2n+2)"),
    ("Aromaat (benzeenring)",
     lambda n: bool(re.search(r"benz|phenyl|phenol|toluene|xylene|aniline|naphth|styrene", n)),
     lambda f: f.get("C", 0) < 6 or verzadigd(f), "minder dan zes koolstofatomen, of verzadigd"),
]
ZEKERHEID_WAARDE = {"laag": 1, "middel": 2, "hoog": 3}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows-console: speciale tekens niet laten crashen
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    start = time.time()
    bib = laad_bibliotheek(PROJECTMAP / "data", alleen_uniek=True)
    meta = bib.metadata
    namen = meta["naam"].str.lower().to_numpy()
    formules = [formule_naar_telling(f) for f in meta["formule"]]
    is_gas = (meta["fase"] == "gas").to_numpy()

    # Per spectrum: voor elke groep de zekerheid (0 = regel ging niet af, 1/2/3 = laag/middel/hoog)
    uitkomst = np.zeros((len(bib), len(GROEPEN)), dtype=np.int8)
    groep_index = {g[0]: i for i, g in enumerate(GROEPEN)}
    for i in range(len(bib)):
        masker = bib.maskers[i] > 0
        pieken = detecteer_pieken(bib.raster[masker], bib.absorbantie[i][masker])
        for b in herken_functionele_groepen(pieken):
            uitkomst[i, groep_index[b.groep]] = ZEKERHEID_WAARDE[b.zekerheid]
        if (i + 1) % 4000 == 0:
            print(f"  {i + 1} / {len(bib)} spectra...", flush=True)

    def p(deel: np.ndarray) -> str:
        return f"{100 * deel.mean():.0f}%" if deel.size else "-"

    rijen, regels_md, regels_fase = [], [], []
    for j, (groep, naam_test, onmogelijk_test, onmogelijk_uitleg) in enumerate(GROEPEN):
        aanwezig = np.array([naam_test(n) for n in namen])
        onmogelijk = np.array([bool(f) and onmogelijk_test(f) for f in formules])
        aanwezig &= ~onmogelijk                     # naam zegt ja maar formule zegt onmogelijk: niet meetellen
        af = uitkomst[:, j] >= 1
        af_zeker = uitkomst[:, j] >= 2
        rij = {
            "groep": groep,
            "n_aanwezig_volgens_naam": int(aanwezig.sum()),
            "trefkans_elke_zekerheid": float(af[aanwezig].mean()) if aanwezig.any() else np.nan,
            "trefkans_middel_of_hoog": float(af_zeker[aanwezig].mean()) if aanwezig.any() else np.nan,
            "trefkans_gas": float(af[aanwezig & is_gas].mean()) if (aanwezig & is_gas).any() else np.nan,
            "trefkans_niet_gas": float(af[aanwezig & ~is_gas].mean()) if (aanwezig & ~is_gas).any() else np.nan,
            "n_onmogelijk_volgens_formule": int(onmogelijk.sum()),
            "vals_alarm_elke_zekerheid": float(af[onmogelijk].mean()) if onmogelijk.any() else np.nan,
            "vals_alarm_middel_of_hoog": float(af_zeker[onmogelijk].mean()) if onmogelijk.any() else np.nan,
            "vals_alarm_hoog": float((uitkomst[onmogelijk, j] == 3).mean()) if onmogelijk.any() else np.nan,
        }
        rijen.append(rij)
        regels_md.append(
            f"| {groep} | {rij['n_aanwezig_volgens_naam']} | {p(af[aanwezig])} | {p(af_zeker[aanwezig])} | "
            f"{rij['n_onmogelijk_volgens_formule']} ({onmogelijk_uitleg}) | {p(af[onmogelijk])} | {p(af_zeker[onmogelijk])} | "
            f"{p(uitkomst[onmogelijk, j] == 3)} |"
        )
        regels_fase.append(
            f"| {groep} | {int((aanwezig & is_gas).sum())} | {p(af[aanwezig & is_gas])} | "
            f"{int((aanwezig & ~is_gas).sum())} | {p(af[aanwezig & ~is_gas])} |"
        )
        print(f"{groep:26s} trefkans {p(af[aanwezig]):>4s} (n={aanwezig.sum():5d}; gas {p(af[aanwezig & is_gas]):>4s}, niet-gas {p(af[aanwezig & ~is_gas]):>4s})"
              f"   vals alarm {p(af[onmogelijk]):>4s} / middel+ {p(af_zeker[onmogelijk]):>4s} / hoog {p(uitkomst[onmogelijk, j] == 3):>4s} (n={onmogelijk.sum()})")

    DOCS.mkdir(exist_ok=True)
    pd.DataFrame(rijen).round(4).to_csv(DOCS / "controle_functionele_groepen.csv", index=False, encoding="utf-8")
    rapport = f"""# Controle van de functionele-groepenregels

> Automatisch gemaakt door `scripts/controle_functionele_groepen.py` op {date.today().isoformat()}.
> Alle getallen komen uit een echte run op de {len(bib)} unieke spectra in de bibliotheek.
> Opnieuw draaien: `.venv\\Scripts\\python scripts\\controle_functionele_groepen.py`

## Hoe is dit getest?

De bibliotheek vertelt niet per stof welke functionele groepen erin zitten. We gebruiken daarom:

- **De naam** om stoffen te vinden waar de groep in *hoort* te zitten (bijv. "...nitrile", "...ol", "...acetate").
  Het percentage van die spectra waarbij de regel afgaat is de **trefkans**. Naamherkenning is grof, dus dit is
  een indicatie.
- **De molecuulformule** om stoffen te vinden waar de groep *onmogelijk* in kan zitten (bijv. geen stikstof → geen
  nitril). Gaat de regel daar toch af, dan is dat zeker een **vals alarm**. Dit percentage is exact.

## Resultaat per regel

| Groep | Spectra waar de groep volgens de naam in zit | Trefkans (elke zekerheid) | Trefkans (middel of hoog) | Spectra waar de groep onmogelijk is | Vals alarm (elke zekerheid) | Vals alarm (middel of hoog) | Vals alarm (hoog) |
|---|---|---|---|---|---|---|---|
{chr(10).join(regels_md)}

## Gasfase tegenover vloeistof/vast/oplossing (trefkans, elke zekerheid)

| Groep | Aantal gas | Trefkans gas | Aantal niet-gas | Trefkans niet-gas |
|---|---|---|---|---|
{chr(10).join(regels_fase)}

## Hoe lees je dit?

- Een **hoge trefkans** betekent: als de groep er is, ziet de regel hem meestal.
- Een **laag vals alarm** betekent: als de regel afgaat, is dat zelden onzin.
- De zekerheid die de app toont (hoog / middel / laag) is bedoeld als rangorde: de kolommen "vals alarm" laten
  zien dat een melding met zekerheid *hoog* minder vaak onterecht is dan een met *laag*.
- Geen enkele regel is perfect. Daarom is dit in de app een **uitleg bij de top 5 en geen beslissing**.

Rekentijd: {time.time() - start:.0f} s.
"""
    (DOCS / "controle_functionele_groepen.md").write_text(rapport, encoding="utf-8")
    print(f"Rapport geschreven naar {DOCS / 'controle_functionele_groepen.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
