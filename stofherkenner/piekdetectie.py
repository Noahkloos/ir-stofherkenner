"""Piekdetectie: waar zitten de absorptiebanden in het spectrum?

Het idee in vier stappen (zie ook notebooks/piekdetectie_en_matching.ipynb):

1. GLADMAKEN (smoothing)
   Een gemeten spectrum bevat ruis: kleine, willekeurige schommelingen. Met een
   Savitzky-Golay-filter maken we het spectrum glad. Dat filter legt door elk
   groepje naast elkaar liggende punten een vloeiend boogje (een polynoom) en
   neemt de waarde van dat boogje. Voordeel boven een simpel gemiddelde: de
   hoogte en breedte van echte pieken blijven veel beter behouden.

2. RUISNIVEAU SCHATTEN
   We moeten weten hoe groot de ruis is om te kunnen zeggen wat "te klein om
   een piek te zijn" betekent. We kijken naar het verschil tussen het ruwe en
   het gladgemaakte spectrum: wat overblijft is vooral ruis. Van dat restant
   nemen we de MAD (median absolute deviation): de mediaan van de absolute
   afwijkingen. De MAD is "robuust": een paar grote uitschieters (echte
   pieken) trekken het getal niet omhoog, wat bij een gewone
   standaarddeviatie wel gebeurt. Voor gewone (normaal verdeelde) ruis geldt:
   standaarddeviatie = 1,4826 x MAD.

3. DREMPEL KIEZEN
   Een bult telt pas als piek als zijn PROMINENTIE groter is dan
   - een veelvoud van de ruis (standaard 5x), EN
   - een klein percentage van de hoogste piek (standaard 3%).
   Prominentie = hoe ver een piek boven zijn omgeving uitsteekt: je meet vanaf
   de top omlaag tot het hoogste "dal" dat je moet oversteken om bij een
   hogere piek te komen. Een klein bobbeltje op de flank van een grote piek
   heeft dus een kleine prominentie, ook al ligt het hoog.

4. MINIMALE BREEDTE
   Ruis of een storing geeft soms een enkele uitschieter van 1 punt breed. Een
   echte absorptieband is altijd een paar punten breed. Te smalle pieken vallen
   af. Let op: dit meten we in het RUWE spectrum. Gladmaken smeert een
   uitschieter namelijk uit, waardoor hij op een smalle echte piek gaat lijken.

Het zoeken zelf doet ``scipy.signal.find_peaks``: die vindt alle lokale maxima
en filtert ze op prominentie en breedte.
"""

from __future__ import annotations

from dataclasses import dataclass

import warnings

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter

# --- Standaardinstellingen (gelden voor het raster van 4 cm^-1) -------------
SMOOTH_VENSTER = 7          # aantal punten voor Savitzky-Golay (7 x 4 = 28 cm^-1 breed)
SMOOTH_GRAAD = 3            # graad van het polynoom (het "boogje")
RUIS_FACTOR = 5.0           # piek moet minstens 5x de ruis boven zijn omgeving uitsteken
MIN_RELATIEVE_PROMINENTIE = 0.03   # ... en minstens 3% van de hoogste piek
MIN_BREEDTE_PUNTEN = 1.5    # minimale breedte op halve hoogte in het RUWE spectrum, in rasterpunten (= 6 cm^-1)


@dataclass
class Piek:
    """Een gevonden piek."""

    golfgetal: float      # positie van de top (cm^-1)
    hoogte: float         # hoogte van de top in het gladgemaakte spectrum
    prominentie: float    # hoe ver de piek boven zijn omgeving uitsteekt
    breedte: float        # breedte op halve hoogte (cm^-1)

    @property
    def is_breed(self) -> bool:
        """Brede band (zoals een O-H met waterstofbruggen): breder dan 100 cm^-1."""
        return self.breedte >= 100.0


def maak_glad(y: np.ndarray, venster: int = SMOOTH_VENSTER, graad: int = SMOOTH_GRAAD) -> np.ndarray:
    """Stap 1: maak het spectrum glad met een Savitzky-Golay-filter.

    ``venster`` is het aantal punten waar telkens een boogje doorheen gelegd
    wordt (moet oneven zijn); ``graad`` is de graad van dat boogje.
    """
    y = np.asarray(y, dtype=float)
    if venster % 2 == 0:
        venster += 1                         # het venster moet een oneven aantal punten hebben
    if y.size <= venster:
        return y.copy()                      # te weinig punten om glad te maken
    return savgol_filter(y, window_length=venster, polyorder=graad)


def schat_ruis(y: np.ndarray, y_glad: np.ndarray | None = None) -> float:
    """Stap 2: schat het ruisniveau (als standaarddeviatie) met de MAD.

    We nemen het restant (ruw min glad). Dat bestaat bijna helemaal uit ruis.
    De MAD van dat restant, maal 1,4826, is een robuuste schatting van de
    standaarddeviatie van de ruis.
    """
    y = np.asarray(y, dtype=float)
    if y_glad is None:
        y_glad = maak_glad(y)
    restant = y - y_glad
    mad = np.median(np.abs(restant - np.median(restant)))
    return float(1.4826 * mad)


def ruwe_breedte(y: np.ndarray, top: int) -> float:
    """Breedte op halve hoogte van een piek in het RUWE (niet gladgemaakte) spectrum, in punten.

    ``top`` is de plek van de piek in het gladgemaakte spectrum; de echte top
    in het ruwe spectrum kan een of twee punten ernaast liggen, dus die zoeken
    we eerst op. Een losse uitschieter is hier ongeveer 1 punt breed.
    """
    begin, eind = max(top - 2, 0), min(top + 3, y.size)
    ruwe_top = begin + int(np.argmax(y[begin:eind]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")              # scipy waarschuwt als de top geen strikt maximum is
        return float(peak_widths(y, [ruwe_top], rel_height=0.5)[0][0])


def detecteer_pieken(
    golfgetal: np.ndarray,
    absorbantie: np.ndarray,
    ruis_factor: float = RUIS_FACTOR,
    min_relatieve_prominentie: float = MIN_RELATIEVE_PROMINENTIE,
    min_breedte_punten: float = MIN_BREEDTE_PUNTEN,
    venster: int = SMOOTH_VENSTER,
    graad: int = SMOOTH_GRAAD,
) -> list[Piek]:
    """Vind de pieken in een absorbantiespectrum.

    ``golfgetal`` moet oplopend en met vaste stap zijn (zoals het raster van de
    app). Geeft een lijst ``Piek``-objecten terug, gesorteerd op golfgetal.
    """
    golfgetal = np.asarray(golfgetal, dtype=float)
    absorbantie = np.asarray(absorbantie, dtype=float)
    if golfgetal.size < 5:
        return []

    # Stap 1: gladmaken
    glad = maak_glad(absorbantie, venster, graad)

    # Stap 2: ruisniveau schatten
    ruis = schat_ruis(absorbantie, glad)

    # Stap 3: drempel = de strengste van (veelvoud van de ruis) en (percentage van de hoogste piek)
    bereik = float(glad.max() - glad.min())
    if bereik <= 0:
        return []                            # volledig vlak spectrum: geen pieken
    drempel = max(ruis_factor * ruis, min_relatieve_prominentie * bereik)

    # Lokale maxima zoeken die ver genoeg boven hun omgeving uitsteken
    toppen, eigenschappen = find_peaks(
        glad,
        prominence=drempel,                  # moet ver genoeg boven de omgeving uitsteken
        width=0,                             # laat scipy ook de breedte uitrekenen
        rel_height=0.5,                      # breedte meten op halve hoogte
    )

    # Stap 4: te smalle pieken (losse uitschieters) weggooien, gemeten in het ruwe spectrum
    stap = float(abs(golfgetal[1] - golfgetal[0]))   # cm^-1 per rasterpunt
    pieken = [
        Piek(
            golfgetal=float(golfgetal[top]),
            hoogte=float(glad[top]),
            prominentie=float(eigenschappen["prominences"][i]),
            breedte=float(eigenschappen["widths"][i] * stap),
        )
        for i, top in enumerate(toppen)
        if ruwe_breedte(absorbantie, top) >= min_breedte_punten
    ]
    return sorted(pieken, key=lambda p: p.golfgetal)


def pieken_in_gebied(pieken: list[Piek], laag: float, hoog: float) -> list[Piek]:
    """Geef de pieken waarvan de top tussen ``laag`` en ``hoog`` cm^-1 ligt."""
    return [p for p in pieken if laag <= p.golfgetal <= hoog]
