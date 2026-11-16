"""Voorbewerking: elk spectrum in dezelfde vorm gieten.

Spectra komen in allerlei vormen binnen (golfgetal of golflengte, transmissie
of absorbantie, verschillende resoluties). Om ze eerlijk te kunnen vergelijken
zetten we ze allemaal om naar:

1. x-as in golfgetal (cm^-1),
2. y-as in absorbantie,
3. een vast raster: 550 t/m 3798 cm^-1 in stappen van 4 cm^-1 (813 punten),
4. basislijn op 0 en hoogste piek op 1 (normaliseren).

Dezelfde stappen worden gebruikt voor de referentiebibliotheek EN voor het
geuploade spectrum. Dat is essentieel: anders vergelijk je appels met peren.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import binary_erosion
from scipy.signal import savgol_filter

from .jcamp_lezen import Spectrum

# --- Het vaste raster -------------------------------------------------------
# Onder ~500 en boven ~3900 cm^-1 zit in de NIST-data vaak storing, dus die
# randen laten we weg.
RASTER_MIN = 550.0
RASTER_MAX = 3800.0
RASTER_STAP = 4.0
RASTER = np.arange(RASTER_MIN, RASTER_MAX + 0.001, RASTER_STAP)   # 550, 554, ..., 3798

# Ondergrens voor transmissie: 1% (T = 0,01). Zonder ondergrens zou
# A = -log10(0) oneindig worden. Met deze grens is de absorbantie maximaal 2.
T_ONDERGRENS = 0.01

# Een spectrum moet minstens dit deel van het raster bedekken om bruikbaar te zijn.
MIN_DEKKING = 0.5

# Instellingen voor de "vergelijkingsvorm" (zie de functie vergelijkingsvorm).
# Gekozen op basis van metingen: zie docs/vergelijking_voorbewerking.md.
COMPRESSIE = "log"            # "geen", "wortel", "derdemachtswortel" of "log"
LOG_FACTOR = 100.0            # bij "log": log(1 + 100 x absorbantie)
AFGELEIDE_VENSTER = 9         # aantal rasterpunten voor de afgeleide (0 = geen afgeleide)


class VoorbewerkingFout(Exception):
    """Het spectrum kan niet worden omgerekend (met Nederlandse uitleg)."""


@dataclass
class VoorbewerktSpectrum:
    """Een spectrum op het vaste raster, klaar om te vergelijken."""

    absorbantie: np.ndarray   # genormaliseerde absorbantie (0..1) op RASTER; 0 buiten het meetbereik
    masker: np.ndarray        # True waar het spectrum echt gemeten is
    x_soort: str              # "golfgetal", "micrometer" of "nanometer"
    y_soort: str              # "transmissie", "absorbantie" of "absorptiecoefficient"
    dekking: float            # deel van het raster dat gemeten is (0..1)


# --- Eenheden herkennen -----------------------------------------------------

def herken_x_eenheid(tekst: str) -> str | None:
    """Vertaal de tekst uit ##XUNITS naar "golfgetal", "micrometer" of "nanometer".

    Geeft None als de eenheid onbekend is.
    """
    t = tekst.strip().upper().replace(" ", "")
    if t in ("1/CM", "CM-1", "CM^-1", "CM**-1", "/CM", "WAVENUMBER", "WAVENUMBERS", "WAVENUMBER(CM-1)", "CM⁻¹"):
        return "golfgetal"
    if t in ("MICROMETERS", "MICROMETER", "MICRONS", "MICRON", "UM", "µM", "ΜM"):
        return "micrometer"
    if t in ("NANOMETERS", "NANOMETER", "NM"):
        return "nanometer"
    return None


def herken_y_eenheid(tekst: str) -> str | None:
    """Vertaal de tekst uit ##YUNITS naar "transmissie", "absorbantie" of
    "absorptiecoefficient". Geeft None als de eenheid niet ondersteund wordt
    (bijvoorbeeld reflectie of brekingsindex).
    """
    t = tekst.strip().upper()
    if "TRANSMI" in t or t in ("%T", "T", "% T"):
        return "transmissie"
    if "ABSORBANCE" in t or t in ("A", "ABS", "AU", "A.U."):
        return "absorbantie"
    # NIST "QUANT-IR": absorptiecoefficient, recht evenredig met absorbantie.
    if "MICROMOL/MOL" in t or "ABSORPTIVITY" in t or "ABSORPTION COEFFICIENT" in t:
        return "absorptiecoefficient"
    return None


# --- Omrekenen --------------------------------------------------------------

def x_naar_golfgetal(x: np.ndarray, x_soort: str) -> np.ndarray:
    """Reken de x-as om naar golfgetal in cm^-1.

    Golflengte en golfgetal zijn elkaars omgekeerde:
        golfgetal (cm^-1) = 10 000 / golflengte (micrometer)
        golfgetal (cm^-1) = 10 000 000 / golflengte (nanometer)
    """
    x = np.asarray(x, dtype=float)
    if x_soort == "golfgetal":
        return x
    if np.any(x <= 0):
        raise VoorbewerkingFout("de golflengte-as bevat nul of negatieve waarden")
    if x_soort == "micrometer":
        return 10_000.0 / x
    if x_soort == "nanometer":
        return 10_000_000.0 / x
    raise VoorbewerkingFout(f"onbekende x-eenheid: {x_soort}")


def transmissie_als_fractie(t: np.ndarray, eenheid_tekst: str = "") -> np.ndarray:
    """Zorg dat transmissie als fractie (0..1) staat in plaats van als percentage.

    We herkennen procenten aan een %-teken in de eenheid of aan waarden die
    duidelijk boven 1 uitkomen (een fractie komt niet boven ~1).
    """
    t = np.asarray(t, dtype=float)
    if "%" in eenheid_tekst or "PERCENT" in eenheid_tekst.upper() or np.nanmax(t) > 2.0:
        return t / 100.0
    return t


def y_naar_absorbantie(y: np.ndarray, y_soort: str, eenheid_tekst: str = "") -> np.ndarray:
    """Reken de y-as om naar absorbantie.

    Wet van Lambert-Beer:  A = -log10(T), met T de transmissie als fractie.
    Voorbeeld: T = 0,10 (10% van het licht komt door)  ->  A = 1.
    """
    y = np.asarray(y, dtype=float)
    if y_soort == "transmissie":
        t = transmissie_als_fractie(y, eenheid_tekst)
        t = np.clip(t, T_ONDERGRENS, None)     # ondergrens voorkomt log(0)
        return -np.log10(t)
    return y                                    # absorbantie (of iets dat daar evenredig mee is)


def op_raster(golfgetal: np.ndarray, waarde: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Zet een spectrum op het vaste raster van 4 cm^-1.

    - Heeft het spectrum MEER punten dan het raster (hoge resolutie), dan nemen
      we per rasterpunt het gemiddelde van alle meetpunten binnen +/- 2 cm^-1.
      Daardoor zien een hoge-resolutie- en een lage-resolutie-meting van
      hetzelfde spectrum er op het raster (bijna) hetzelfde uit.
    - Heeft het spectrum MINDER punten, dan interpoleren we lineair (rechte
      lijntjes tussen de meetpunten).

    Geeft (waarden op het raster, masker) terug. Het masker is True op de
    rasterpunten die binnen het gemeten bereik liggen.
    """
    golfgetal = np.asarray(golfgetal, dtype=float)
    waarde = np.asarray(waarde, dtype=float)
    volgorde = np.argsort(golfgetal)                 # np.interp wil oplopende x
    x, y = golfgetal[volgorde], waarde[volgorde]

    masker = (RASTER >= x[0]) & (RASTER <= x[-1])

    # Lineaire interpolatie voor alle rasterpunten
    resultaat = np.interp(RASTER, x, y)

    # Gemiddelde per rasterpunt ("bin") waar genoeg meetpunten in vallen
    bin_index = np.floor((x - (RASTER_MIN - RASTER_STAP / 2)) / RASTER_STAP).astype(np.int64)
    geldig = (bin_index >= 0) & (bin_index < RASTER.size)
    aantal = np.bincount(bin_index[geldig], minlength=RASTER.size)
    som = np.bincount(bin_index[geldig], weights=y[geldig], minlength=RASTER.size)
    genoeg = aantal >= 2
    resultaat[genoeg] = som[genoeg] / aantal[genoeg]

    resultaat[~masker] = 0.0
    return resultaat, masker


def normaliseer(absorbantie: np.ndarray, masker: np.ndarray) -> np.ndarray:
    """Zet de basislijn op 0 en de hoogste piek op 1.

    - Basislijn: we trekken de laagste waarde af (een spectrum "zweeft" vaak
      een beetje boven nul).
    - Schaal: we delen door het maximum. Zo maakt het niet uit hoe dik het
      monster was of hoe geconcentreerd: alleen de VORM van het spectrum telt.
    """
    a = np.array(absorbantie, dtype=float)
    if not masker.any():
        raise VoorbewerkingFout("het spectrum valt volledig buiten het bereik 550-3800 cm^-1")
    a[masker] -= a[masker].min()
    hoogste = a[masker].max()
    if not np.isfinite(hoogste) or hoogste <= 0:
        raise VoorbewerkingFout("het spectrum is volledig vlak (er zijn geen pieken)")
    a /= hoogste
    a[~masker] = 0.0
    return a


# --- Alles achter elkaar ----------------------------------------------------

def bewerk_voor(spectrum: Spectrum) -> VoorbewerktSpectrum:
    """Voer alle voorbewerkingsstappen uit op een ingelezen spectrum."""
    x_soort = herken_x_eenheid(spectrum.x_eenheid)
    if x_soort is None:
        raise VoorbewerkingFout(f"de x-eenheid '{spectrum.x_eenheid}' wordt niet ondersteund")
    y_soort = herken_y_eenheid(spectrum.y_eenheid)
    if y_soort is None:
        raise VoorbewerkingFout(f"de y-eenheid '{spectrum.y_eenheid}' wordt niet ondersteund")

    x, y = np.asarray(spectrum.x, dtype=float), np.asarray(spectrum.y, dtype=float)
    if x.size < 2:
        raise VoorbewerkingFout("het spectrum heeft te weinig punten")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise VoorbewerkingFout("het spectrum bevat ongeldige getallen (NaN of oneindig)")

    golfgetal = x_naar_golfgetal(x, x_soort)
    absorbantie = y_naar_absorbantie(y, y_soort, spectrum.y_eenheid)
    op_het_raster, masker = op_raster(golfgetal, absorbantie)
    dekking = float(masker.mean())
    if dekking < MIN_DEKKING:
        raise VoorbewerkingFout(
            f"het spectrum bedekt maar {dekking:.0%} van het bereik 550-3800 cm^-1 (minimaal {MIN_DEKKING:.0%} nodig)"
        )
    genormaliseerd = normaliseer(op_het_raster, masker)
    return VoorbewerktSpectrum(genormaliseerd, masker, x_soort, y_soort, dekking)


# --- Vergelijkingsvorm ------------------------------------------------------

def comprimeer(absorbantie: np.ndarray, compressie: str = COMPRESSIE) -> np.ndarray:
    """Druk de piekhoogtes samen, zodat zwakke pieken zwaarder meetellen.

    In een IR-spectrum is de POSITIE van een piek veel betrouwbaarder dan de
    HOOGTE: de hoogte hangt af van de concentratie, de laagdikte en de fase.
    Zonder compressie bepaalt de ene hoogste piek bijna de hele score. Met een
    logaritme telt een piek van 1% hoogte nog voor ongeveer 15% mee.
    """
    a = np.clip(np.asarray(absorbantie, dtype=float), 0.0, None)
    if compressie == "geen":
        return a
    if compressie == "wortel":
        return np.sqrt(a)
    if compressie == "derdemachtswortel":
        return np.cbrt(a)
    if compressie == "log":
        return np.log1p(LOG_FACTOR * a)
    raise ValueError(f"onbekende compressie: {compressie!r}")


def vergelijkingsvorm(
    absorbantie: np.ndarray,
    masker: np.ndarray,
    compressie: str = COMPRESSIE,
    afgeleide_venster: int = AFGELEIDE_VENSTER,
) -> np.ndarray:
    """Zet een genormaliseerd spectrum om naar de vorm waarmee we VERGELIJKEN.

    Twee stappen (beide gekozen omdat ze in de evaluatie aantoonbaar helpen):

    1. COMPRESSIE (logaritme): zwakke pieken tellen zwaarder mee, zie
       ``comprimeer``.
    2. EERSTE AFGELEIDE: we vergelijken niet de hoogte van het spectrum maar de
       HELLING (hoe snel het stijgt of daalt). Een scheve of verhoogde
       basislijn, die bij vaste stoffen en oude metingen veel voorkomt, heeft
       bijna geen helling en valt daardoor weg. De afgeleide berekenen we met
       een Savitzky-Golay-filter, dat tegelijk een beetje gladmaakt.

    Werkt voor een enkel spectrum (1 rij) en voor een hele matrix (1 rij per
    spectrum). Het resultaat is geschaald zodat de grootste uitslag 1 is.
    """
    a = np.atleast_2d(np.asarray(absorbantie, dtype=float))
    m = np.atleast_2d(np.asarray(masker)).astype(bool)

    vorm = comprimeer(a, compressie)
    if afgeleide_venster and afgeleide_venster >= 3:
        vorm = savgol_filter(vorm, window_length=afgeleide_venster, polyorder=2, deriv=1, axis=1)
        # Aan de rand van het meetbereik springt het spectrum van "gemeten" naar 0.
        # Die nep-helling halen we weg door de rand (een half venster) op 0 te zetten.
        m = binary_erosion(m, structure=np.ones((1, afgeleide_venster), dtype=bool), border_value=0)
    vorm = vorm * m

    grootste = np.abs(vorm).max(axis=1, keepdims=True)
    grootste[grootste <= 0] = 1.0
    vorm = (vorm / grootste).astype(np.float32)
    return vorm[0] if np.ndim(absorbantie) == 1 else vorm
