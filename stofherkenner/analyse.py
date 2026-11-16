"""De hele analyse van een geupload bestand achter elkaar.

Deze module knoopt de losse stappen aan elkaar, zodat app.py alleen nog hoeft
te TONEN. Zo kunnen de tests precies dezelfde code draaien als de app.

    bestand -> valideren -> inlezen -> voorbewerken -> pieken zoeken
            -> vergelijken met de bibliotheek -> functionele groepen
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .functionele_groepen import Bevinding, herken_functionele_groepen
from .jcamp_lezen import Spectrum
from .matching import STANDAARD_METHODE, Bibliotheek, beoordeel_resultaat, zoek
from .piekdetectie import Piek, detecteer_pieken
from .validatie import valideer_upload
from .voorbewerking import RASTER, VoorbewerkingFout, VoorbewerktSpectrum, bewerk_voor, herken_x_eenheid, x_naar_golfgetal

# Een losse piekentabel of een spectrum met heel weinig punten kunnen we wel
# tonen, maar niet betrouwbaar vergelijken.
MIN_PUNTEN_VOOR_ANALYSE = 50


@dataclass
class Analyse:
    """Alles wat de app over een bestand wil laten zien."""

    spectrum: Spectrum
    golfgetal: np.ndarray                      # x-as in cm^-1 (voor de grafiek)
    waarschuwingen: list[str] = field(default_factory=list)
    voorbewerkt: VoorbewerktSpectrum | None = None
    pieken: list[Piek] = field(default_factory=list)
    top: pd.DataFrame | None = None            # top 5 stoffen (None als er niet gezocht kon worden)
    zoek_waarschuwingen: list[str] = field(default_factory=list)
    bevindingen: list[Bevinding] = field(default_factory=list)
    reden_geen_analyse: str = ""               # ingevuld als alleen de grafiek getoond kan worden
    tijden_ms: dict[str, float] = field(default_factory=dict)   # hoe lang elke stap duurde


def lees_en_valideer(bestandsnaam: str, inhoud: bytes) -> Analyse:
    """Stap 1: controleer het bestand en lees het in (gooit ``ValidatieFout`` bij problemen)."""
    start = time.perf_counter()
    resultaat = valideer_upload(bestandsnaam, inhoud)
    spectrum = resultaat.spectrum
    golfgetal = x_naar_golfgetal(spectrum.x, herken_x_eenheid(spectrum.x_eenheid))
    analyse = Analyse(spectrum=spectrum, golfgetal=golfgetal, waarschuwingen=list(resultaat.waarschuwingen))
    analyse.tijden_ms["valideren en inlezen"] = (time.perf_counter() - start) * 1000
    return analyse


def analyseer(analyse: Analyse, bibliotheek: Bibliotheek | None, methode: str = STANDAARD_METHODE, top_n: int = 5,
              negeer_identiek: bool = False) -> Analyse:
    """Stap 2: voorbewerken, pieken zoeken, vergelijken en functionele groepen bepalen."""
    spectrum = analyse.spectrum
    if spectrum.datablok_soort == "PEAK TABLE" or spectrum.x.size < MIN_PUNTEN_VOOR_ANALYSE:
        analyse.reden_geen_analyse = (
            "Dit bestand bevat alleen een piekentabel of heel weinig meetpunten. De grafiek wordt getoond, "
            "maar voor piekdetectie en vergelijking met de bibliotheek is een volledig spectrum nodig."
        )
        return analyse

    start = time.perf_counter()
    try:
        analyse.voorbewerkt = bewerk_voor(spectrum)
    except VoorbewerkingFout as fout:
        analyse.reden_geen_analyse = f"Het spectrum kan niet verder worden geanalyseerd: {fout}."
        return analyse
    analyse.tijden_ms["voorbewerken"] = (time.perf_counter() - start) * 1000

    # Pieken zoeken op het gemeten deel van het raster
    start = time.perf_counter()
    masker = analyse.voorbewerkt.masker
    analyse.pieken = detecteer_pieken(RASTER[masker], analyse.voorbewerkt.absorbantie[masker])
    analyse.bevindingen = herken_functionele_groepen(analyse.pieken)
    analyse.tijden_ms["pieken en functionele groepen"] = (time.perf_counter() - start) * 1000

    if analyse.voorbewerkt.dekking < 0.9:
        analyse.waarschuwingen.append(
            f"Het spectrum bedekt {analyse.voorbewerkt.dekking:.0%} van het bereik 550–3800 cm⁻¹. "
            "Alleen het gemeten deel wordt vergeleken; pieken buiten dat deel tellen niet mee."
        )

    # Vergelijken met de bibliotheek
    if bibliotheek is not None:
        start = time.perf_counter()
        analyse.top = zoek(bibliotheek, analyse.voorbewerkt.absorbantie, masker, methode, top_n, negeer_identiek)
        analyse.zoek_waarschuwingen = beoordeel_resultaat(analyse.top)
        analyse.tijden_ms["zoeken in de bibliotheek"] = (time.perf_counter() - start) * 1000
    return analyse
