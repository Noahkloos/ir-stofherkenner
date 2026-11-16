"""Spectral library search: het onbekende spectrum vergelijken met de bibliotheek.

Elk spectrum is na de voorbewerking een rij van 813 getallen (een getal per
rasterpunt). Zo'n rij kun je zien als een PUNT of PIJL (vector) in een ruimte
met 813 dimensies. Twee spectra lijken op elkaar als hun vectoren dicht bij
elkaar liggen of dezelfde kant op wijzen. Drie manieren om dat te meten:

- COSINUSGELIJKENIS: de hoek tussen de twee pijlen. Zelfde richting = 1
  (100%), loodrecht = 0. De LENGTE van de pijl telt niet mee, dus het maakt
  niet uit of een spectrum als geheel sterker of zwakker is.
- EUCLIDISCHE AFSTAND: de gewone afstand tussen de twee punten (stelling van
  Pythagoras in 813 dimensies). 0 = identiek. We rekenen hem om naar een score:
  100% x (1 - gemiddelde afwijking per punt).
- PEARSON-CORRELATIE: als cosinus, maar eerst wordt van elk spectrum het
  gemiddelde afgetrokken. Daardoor telt een constante verschuiving niet mee.

We vergelijken niet de kale absorbantie, maar de "vergelijkingsvorm" (logaritme
+ afgeleide, zie ``voorbewerking.vergelijkingsvorm``). Dat geeft aantoonbaar
betere resultaten; zie docs/vergelijking_voorbewerking.md.

Niet elk spectrum bedekt het hele raster (sommige metingen stoppen bij
650 cm^-1). Daarom vergelijken we steeds alleen het stuk dat BEIDE spectra
gemeten hebben. Dat houden we bij met een "masker" (True = gemeten).

Alles is gevectoriseerd met numpy: in plaats van een lus over 18 000 spectra
doen we een paar matrixvermenigvuldigingen. Daardoor duurt een zoekopdracht
door de hele bibliotheek enkele tientallen milliseconden.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .voorbewerking import vergelijkingsvorm

METHODEN = ("cosinus", "pearson", "euclidisch")
STANDAARD_METHODE = "cosinus"     # gekozen op basis van docs/evaluatie.md

# Minimaal aantal rasterpunten dat twee spectra samen gemeten moeten hebben
# (300 punten = 1200 cm^-1). Bij minder overlap is een vergelijking niet eerlijk.
MIN_OVERLAP = 300

# Drempels voor de waarschuwingen in de app. Ze zijn gekozen op basis van de
# scoreverdelingen in de evaluatie (docs/evaluatie.md).
LAGE_SCORE = 65.0          # beste score lager dan dit -> "staat waarschijnlijk niet in de database"
KLEIN_VERSCHIL = 5.0       # nummer 1 en 2 minder dan dit uit elkaar -> "kan niet goed kiezen"

# Een score vanaf deze waarde betekent: dit IS hetzelfde spectrum (bijv. een
# voorbeeldbestand dat zelf in de bibliotheek staat).
IDENTIEK_SCORE = 99.95


@dataclass
class Bibliotheek:
    """De referentiebibliotheek in het geheugen."""

    absorbantie: np.ndarray        # (aantal spectra) x (aantal rasterpunten): om te TONEN
    vectoren: np.ndarray           # zelfde vorm: de vergelijkingsvorm, om te VERGELIJKEN
    vectoren_kwadraat: np.ndarray  # vectoren ** 2, vooraf uitgerekend voor snelheid
    maskers: np.ndarray            # zelfde vorm, 1.0 waar gemeten en 0.0 waar niet
    metadata: pd.DataFrame         # een rij per spectrum (naam, cas, formule, fase, ...)
    raster: np.ndarray             # de golfgetallen van het raster

    def __len__(self) -> int:
        return self.absorbantie.shape[0]


def maak_bibliotheek(
    absorbantie: np.ndarray, maskers: np.ndarray, metadata: pd.DataFrame, raster: np.ndarray, **vorm_opties
) -> Bibliotheek:
    """Maak een ``Bibliotheek`` van genormaliseerde spectra (rekent de vergelijkingsvorm uit)."""
    vectoren = vergelijkingsvorm(absorbantie, maskers > 0, **vorm_opties)
    return Bibliotheek(absorbantie, vectoren, vectoren * vectoren, maskers.astype(np.float32), metadata, raster)


def laad_bibliotheek(datamap: str | Path, alleen_uniek: bool = True) -> Bibliotheek:
    """Laad library.npz en metadata.csv.

    Met ``alleen_uniek=True`` (standaard) worden spectra die als duplicaat
    gemarkeerd zijn weggelaten.
    """
    datamap = Path(datamap)
    with np.load(datamap / "library.npz") as npz:
        absorbantie = npz["spectra"].astype(np.float32)
        maskers = npz["maskers"].astype(np.float32)
        raster = npz["raster"].astype(float)
    metadata = pd.read_csv(datamap / "metadata.csv", dtype=str, keep_default_na=False)
    metadata["duplicaat_van"] = metadata["duplicaat_van"].astype(int)
    if alleen_uniek:
        behouden = (metadata["duplicaat_van"] < 0).to_numpy()
        absorbantie, maskers = absorbantie[behouden], maskers[behouden]
        metadata = metadata[behouden].reset_index(drop=True)
    return maak_bibliotheek(absorbantie, maskers, metadata, raster)


def bereken_scores(
    bib_vectoren: np.ndarray,
    bib_maskers: np.ndarray,
    bib_kwadraat: np.ndarray,
    vraag: np.ndarray,
    vraag_masker: np.ndarray,
    methode: str = STANDAARD_METHODE,
) -> np.ndarray:
    """Bereken de overeenkomstscore (0-100%) van het vraagspectrum met ELK bibliotheekspectrum.

    ``bib_vectoren`` en ``vraag`` zijn spectra in vergelijkingsvorm. ``vraag``
    mag een enkel spectrum zijn (1 rij getallen) of meerdere spectra tegelijk
    (een matrix, 1 rij per spectrum; handig voor de evaluatie).
    Geeft een matrix terug: (aantal vraagspectra) x (aantal bibliotheekspectra).

    Uitleg van de afkortingen in de code (per paar spectra, over hun overlap):
      n   = aantal gemeenschappelijke rasterpunten
      Sxy = som van (vraag x bibliotheek)
      Sxx = som van vraag^2          Syy = som van bibliotheek^2
      Sx  = som van vraag            Sy  = som van bibliotheek
    Al deze sommen krijgen we voor alle paren tegelijk met een matrixproduct (@).
    """
    q = np.atleast_2d(np.asarray(vraag, dtype=np.float32))
    mq = np.atleast_2d(np.asarray(vraag_masker, dtype=np.float32))
    q = q * mq                                   # zeker weten: 0 buiten het eigen meetbereik

    n = mq @ bib_maskers.T                       # aantal gemeenschappelijke punten
    sxy = q @ bib_vectoren.T                     # bibliotheek is al 0 buiten zijn masker
    sxx = (q * q) @ bib_maskers.T                # vraag^2, alleen waar de bibliotheek gemeten heeft
    syy = mq @ bib_kwadraat.T                    # bibliotheek^2, alleen waar de vraag gemeten heeft
    veilig_n = np.maximum(n, 1.0)                # voorkomt delen door nul

    with np.errstate(divide="ignore", invalid="ignore"):
        if methode == "cosinus":
            # cos(hoek) = Sxy / (lengte vraag x lengte bibliotheek)
            score = sxy / np.sqrt(sxx * syy)
        elif methode == "pearson":
            # als cosinus, maar met het gemiddelde van elk spectrum eraf getrokken
            sx = q @ bib_maskers.T
            sy = mq @ bib_vectoren.T
            teller = sxy - sx * sy / veilig_n
            noemer = np.sqrt((sxx - sx * sx / veilig_n) * (syy - sy * sy / veilig_n))
            score = teller / noemer
        elif methode == "euclidisch":
            # afstand^2 = som (vraag - bibliotheek)^2 = Sxx - 2 Sxy + Syy
            afstand_kwadraat = np.maximum(sxx - 2.0 * sxy + syy, 0.0)
            gemiddelde_afwijking = np.sqrt(afstand_kwadraat / veilig_n)   # RMS-afwijking per rasterpunt
            score = 1.0 - gemiddelde_afwijking
        else:
            raise ValueError(f"onbekende methode: {methode!r} (kies uit {METHODEN})")

    score = np.nan_to_num(score, nan=0.0, posinf=0.0, neginf=0.0)
    score[n < MIN_OVERLAP] = 0.0                 # te weinig overlap: niet vergelijkbaar
    return np.clip(score, 0.0, 1.0) * 100.0


def zoek(
    bibliotheek: Bibliotheek,
    absorbantie: np.ndarray,
    masker: np.ndarray,
    methode: str = STANDAARD_METHODE,
    top_n: int = 5,
    negeer_identiek: bool = False,
) -> pd.DataFrame:
    """Zoek de ``top_n`` best passende STOFFEN voor een vraagspectrum.

    Met ``negeer_identiek=True`` doen referentiespectra die (vrijwel) exact
    gelijk zijn aan het vraagspectrum niet mee. Zo kun je een spectrum dat zelf
    in de bibliotheek staat toch eerlijk testen ("leave-one-out").

    ``absorbantie`` en ``masker`` komen uit ``voorbewerking.bewerk_voor``; de
    omzetting naar de vergelijkingsvorm gebeurt hier. Van elke stof telt alleen
    het best passende spectrum (een stof kan meerdere spectra in de bibliotheek
    hebben). Geeft een tabel terug met per stof: naam, cas, formule, fase,
    score en de rij-index van het beste spectrum.
    """
    vraag = vergelijkingsvorm(absorbantie, masker)
    scores = bereken_scores(
        bibliotheek.vectoren, bibliotheek.maskers, bibliotheek.vectoren_kwadraat, vraag, masker, methode
    )[0]
    if negeer_identiek:
        scores = np.where(scores >= IDENTIEK_SCORE, -1.0, scores)
    volgorde = np.argsort(-scores)               # hoogste score eerst

    gezien: set[str] = set()
    rijen = []
    for index in volgorde:
        rij = bibliotheek.metadata.iloc[index]
        if rij["nist_id"] in gezien:
            continue                             # van deze stof hebben we al een beter spectrum
        gezien.add(rij["nist_id"])
        rijen.append({
            "rang": len(rijen) + 1,
            "naam": rij["naam"],
            "cas": rij["cas"],
            "formule": rij["formule"],
            "fase": rij["fase"],
            "score": float(scores[index]),
            "nist_id": rij["nist_id"],
            "bestand": rij["bestand"],
            "rij_index": int(index),
        })
        if len(rijen) >= top_n:
            break
    return pd.DataFrame(rijen)


def beoordeel_resultaat(top: pd.DataFrame) -> list[str]:
    """Geef waarschuwingen bij een onbetrouwbaar zoekresultaat (in gewone taal)."""
    waarschuwingen: list[str] = []
    if top.empty:
        return ["Er is geen enkel vergelijkbaar spectrum gevonden."]
    beste = float(top.iloc[0]["score"])
    if beste < LAGE_SCORE:
        waarschuwingen.append(
            f"De beste score is laag ({beste:.1f}%). Waarschijnlijk staat deze stof niet in de database, "
            "is het een mengsel, of is het spectrum op een andere manier gemeten dan de referentie "
            "(bijv. ATR of vaste stof tegenover een gasfase-referentie)."
        )
    if len(top) > 1:
        verschil = beste - float(top.iloc[1]["score"])
        if verschil < KLEIN_VERSCHIL:
            waarschuwingen.append(
                f"De nummers 1 en 2 liggen heel dicht bij elkaar (verschil {verschil:.1f} procentpunt). "
                "Het systeem kan niet betrouwbaar tussen deze stoffen kiezen; het gaat vaak om isomeren "
                "of stoffen uit dezelfde reeks. Gebruik aanvullende gegevens (bijv. kookpunt, MS of NMR)."
            )
    return waarschuwingen
