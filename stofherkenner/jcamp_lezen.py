"""Een JCAMP-DX-bestand (IR-spectrum) omzetten naar getallen.

JCAMP-DX is een tekstformaat. Het bestaat uit:
- een KOP met regels als ``##TITLE=Acetone`` (label = waarde), en
- een DATABLOK met de meetpunten, bijvoorbeeld::

      ##XYDATA=(X++(Y..Y))
      450.0 40 76 71 59
      470.0 67 74 97 132
      ##END=

  Elke dataregel begint met een x-waarde, daarna volgen de y-waarden van de
  punten vanaf die x. De echte waarden krijg je door te vermenigvuldigen met
  ##XFACTOR en ##YFACTOR.

Deze module leest alleen; de strenge controle (is dit wel een geldig bestand?)
staat in ``validatie.py``. Alle fouten worden gemeld als ``JcampFout`` met een
Nederlandse uitleg, zodat de app nooit crasht op een vreemd bestand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np


class JcampFout(Exception):
    """Het bestand kon niet als JCAMP-DX worden gelezen (met Nederlandse uitleg)."""


@dataclass
class Spectrum:
    """Een ingelezen spectrum, nog in de eenheden van het bestand."""

    titel: str
    x: np.ndarray                      # x-waarden (al vermenigvuldigd met XFACTOR)
    y: np.ndarray                      # y-waarden (al vermenigvuldigd met YFACTOR)
    x_eenheid: str                     # tekst uit ##XUNITS, bijv. "1/CM" of "MICROMETERS"
    y_eenheid: str                     # tekst uit ##YUNITS, bijv. "TRANSMITTANCE"
    cas: str = ""                      # CAS-nummer uit ##CAS REGISTRY NO (kan leeg zijn)
    formule: str = ""                  # molecuulformule uit ##MOLFORM (kan leeg zijn)
    toestand: str = ""                 # ##STATE, bijv. "gas" of "SOLID (KBr PELLET)"
    datablok_soort: str = "XYDATA"     # "XYDATA", "XYPOINTS" of "PEAK TABLE"
    npoints_label: int | None = None   # waarde van ##NPOINTS (None als het label ontbreekt)
    aantal_blokken: int = 1            # hoeveel spectra er in het bestand stonden
    labels: dict[str, str] = field(default_factory=dict)  # alle labels uit de kop


# Labels waar een datablok mee begint
DATABLOK_LABELS = ("XYDATA", "XYPOINTS", "PEAK TABLE")

# Een "gewoon" getal, zoals 12, -3.5, .25 of 1.2E-3
_GETAL = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")

# --- ASDF: de gecomprimeerde schrijfwijze van JCAMP-DX ----------------------
# Sommige apparaten slaan getallen compact op: een LETTER vervangt dan het
# eerste cijfer en het plus/min-teken. Voorbeeld: "A23" = +123, "a23" = -123.
#   SQZ ("squeeze"):  @=0, A..I = +1..+9, a..i = -1..-9      -> een gewone waarde
#   DIF (verschil):   %=0, J..R = +1..+9, j..r = -1..-9      -> verschil met vorige waarde
#   DUP (herhaling):  S..Z = 2..9, s = 9                     -> herhaal vorige waarde
_SQZ = {"@": "0", **{c: str(i + 1) for i, c in enumerate("ABCDEFGHI")},
        **{c: "-" + str(i + 1) for i, c in enumerate("abcdefghi")}}
_DIF = {"%": "0", **{c: str(i + 1) for i, c in enumerate("JKLMNOPQR")},
        **{c: "-" + str(i + 1) for i, c in enumerate("jklmnopqr")}}
_DUP = {**{c: i + 2 for i, c in enumerate("STUVWXYZ")}, "s": 9}

_ASDF_TOKEN = re.compile(
    r"([@A-Ia-i%J-Rj-rS-Zs]\d*\.?\d*)"                      # letter + cijfers (SQZ, DIF of DUP)
    r"|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"         # gewoon getal
)


# --- Kop lezen --------------------------------------------------------------

def splits_in_blokken(tekst: str) -> list[str]:
    """Splits een bestand in losse spectra (blokken).

    Een bestand kan meerdere spectra achter elkaar bevatten; elk blok begint met
    ``##TITLE=``. Geeft een lijst met de tekst van elk blok.
    """
    starts = [m.start() for m in re.finditer(r"^[ \t]*##TITLE\s*=", tekst, flags=re.MULTILINE | re.IGNORECASE)]
    if not starts:
        return [tekst]
    grenzen = starts + [len(tekst)]
    return [tekst[grenzen[i]:grenzen[i + 1]] for i in range(len(starts))]


def lees_labels(bloktekst: str) -> tuple[dict[str, str], str, list[str]]:
    """Lees de kop van een blok.

    Geeft terug:
    - een woordenboek {LABEL: waarde} (labelnamen in hoofdletters),
    - de soort datablok ("XYDATA", "XYPOINTS", "PEAK TABLE" of "" als er geen is),
    - de regels van het datablok (alles tussen het datablok-label en ##END).
    """
    labels: dict[str, str] = {}
    soort = ""
    dataregels: list[str] = []
    in_data = False
    for regel in bloktekst.splitlines():
        kaal = regel.strip()
        if kaal.startswith("##"):
            naam, _, waarde = kaal[2:].partition("=")
            naam = naam.strip().upper()
            waarde = waarde.split("$$")[0].strip()      # "$$" begint een opmerking
            if in_data:
                # Een nieuw label betekent: het datablok is afgelopen.
                in_data = False
            if naam in DATABLOK_LABELS and not soort:
                soort = naam
                in_data = True
                labels[naam] = waarde
            elif naam and naam not in labels:
                labels[naam] = waarde
        elif in_data and kaal and not kaal.startswith("$$"):
            dataregels.append(kaal)
    return labels, soort, dataregels


def _als_getal(labels: dict[str, str], naam: str, standaard: float | None = None) -> float | None:
    """Haal een label op als getal; geeft ``standaard`` als het ontbreekt of geen getal is."""
    waarde = labels.get(naam, "")
    m = _GETAL.search(waarde.replace(",", "."))
    if not m:
        return standaard
    try:
        return float(m.group(0))
    except ValueError:
        return standaard


# --- Datablok lezen ---------------------------------------------------------

def _ontleed_asdf_regel(regel: str) -> list[float]:
    """Zet een (mogelijk gecomprimeerde) dataregel om naar een lijst getallen.

    De eerste waarde is de x-waarde, de rest zijn y-waarden.
    """
    waarden: list[float] = []
    vorige_was_dif = False
    laatste_dif = 0.0
    for m in _ASDF_TOKEN.finditer(regel):
        token = m.group(0)
        eerste = token[0]
        if m.group(2) is not None:                       # gewoon getal
            waarden.append(float(token))
            vorige_was_dif = False
        elif eerste in _SQZ:                             # SQZ: gewone waarde, compact geschreven
            waarden.append(float(_SQZ[eerste] + token[1:]))
            vorige_was_dif = False
        elif eerste in _DIF:                             # DIF: verschil met de vorige waarde
            if not waarden:
                raise JcampFout("gecomprimeerde data begint met een verschil-waarde")
            laatste_dif = float(_DIF[eerste] + token[1:])
            waarden.append(waarden[-1] + laatste_dif)
            vorige_was_dif = True
        elif eerste in _DUP:                             # DUP: herhaal het vorige
            if not waarden:
                raise JcampFout("gecomprimeerde data begint met een herhaal-teken")
            aantal = int(_DUP[eerste] if len(token) == 1 else str(_DUP[eerste]) + token[1:]) - 1
            if aantal > 100_000:
                raise JcampFout("onrealistisch groot herhaal-getal in de data")
            for _ in range(aantal):
                # Na een DIF herhaal je het VERSCHIL, anders de waarde zelf.
                waarden.append(waarden[-1] + laatste_dif if vorige_was_dif else waarden[-1])
    return waarden


def _lees_xydata(dataregels: list[str], labels: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    """Lees een ``##XYDATA=(X++(Y..Y))``-blok.

    Per regel: eerst de x van het eerste punt, daarna alleen y-waarden. De
    x-waarden daartussen rekenen we zelf uit met een vaste stapgrootte.
    """
    x_factor = _als_getal(labels, "XFACTOR", 1.0) or 1.0
    y_factor = _als_getal(labels, "YFACTOR", 1.0) or 1.0

    regel_x: list[float] = []        # x-waarde aan het begin van elke regel
    regel_n: list[int] = []          # aantal y-waarden op elke regel
    alle_y: list[float] = []
    dif_gebruikt = False

    for regel in dataregels:
        try:
            # Snelle route: gewone getallen gescheiden door spaties.
            getallen = [float(deel) for deel in regel.replace(",", " ").split()]
        except ValueError:
            # Langzame route: getallen aan elkaar geplakt of gecomprimeerd (ASDF).
            if re.search(r"[^0-9eE+\-.,\s@A-Za-z%]", regel):
                raise JcampFout(f"het datablok bevat tekens die geen getallen zijn: '{regel[:40]}'")
            if re.search(r"[J-Rj-r%]", regel):
                dif_gebruikt = True
            getallen = _ontleed_asdf_regel(regel)
        if len(getallen) < 2:
            raise JcampFout(f"een dataregel bevat geen y-waarden: '{regel[:40]}'")
        regel_x.append(getallen[0])
        regel_n.append(len(getallen) - 1)
        alle_y.extend(getallen[1:])

    if not alle_y:
        raise JcampFout("het datablok is leeg")

    # Bij DIF-compressie herhaalt elke regel het laatste punt van de vorige regel
    # als controle ("y-check"). Dat dubbele punt halen we weg.
    if dif_gebruikt and len(regel_n) > 1:
        y_schoon: list[float] = []
        positie = 0
        for i, n in enumerate(regel_n):
            stuk = alle_y[positie:positie + n]
            positie += n
            if i < len(regel_n) - 1 and n > 1:
                stuk = stuk[:-1]
                regel_n[i] = n - 1
            y_schoon.extend(stuk)
        alle_y = y_schoon

    y = np.asarray(alle_y, dtype=float) * y_factor
    regel_x_arr = np.asarray(regel_x, dtype=float) * x_factor
    aantallen = np.asarray(regel_n, dtype=int)
    n_totaal = int(aantallen.sum())

    # Stapgrootte in x bepalen. Voorkeur: uit FIRSTX en LASTX (dat is het
    # nauwkeurigst); anders uit DELTAX; anders uit de x-waarden van de regels.
    first_x = _als_getal(labels, "FIRSTX")
    last_x = _als_getal(labels, "LASTX")
    delta_x = _als_getal(labels, "DELTAX")
    stap: float | None = None
    if first_x is not None and last_x is not None and n_totaal > 1 and last_x != first_x:
        stap = (last_x - first_x) / (n_totaal - 1)
    elif delta_x:
        stap = delta_x
    elif len(regel_x_arr) > 1 and aantallen[0] > 0:
        stap = (regel_x_arr[1] - regel_x_arr[0]) / aantallen[0]
    if stap is None or stap == 0:
        if n_totaal == 1:
            stap = 0.0
        else:
            raise JcampFout("de stapgrootte van de x-as is niet te bepalen (FIRSTX/LASTX/DELTAX ontbreken)")

    # x voor elk punt = x aan het begin van de regel + (plek op de regel) * stap
    begin_index = np.concatenate(([0], np.cumsum(aantallen)[:-1]))
    plek_op_regel = np.arange(n_totaal) - np.repeat(begin_index, aantallen)
    x = np.repeat(regel_x_arr, aantallen) + plek_op_regel * stap
    return x, y


def _lees_xy_paren(dataregels: list[str], labels: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    """Lees een ``(XY..XY)``-blok (XYPOINTS of PEAK TABLE): losse x,y-paren."""
    x_factor = _als_getal(labels, "XFACTOR", 1.0) or 1.0
    y_factor = _als_getal(labels, "YFACTOR", 1.0) or 1.0
    getallen: list[float] = []
    for regel in dataregels:
        if re.search(r"[^0-9eE+\-.,;\s]", regel):
            raise JcampFout(f"het datablok bevat tekens die geen getallen zijn: '{regel[:40]}'")
        getallen.extend(float(t) for t in _GETAL.findall(regel))
    if len(getallen) < 2 or len(getallen) % 2 != 0:
        raise JcampFout("het datablok bevat geen kloppende x,y-paren")
    paren = np.asarray(getallen, dtype=float).reshape(-1, 2)
    return paren[:, 0] * x_factor, paren[:, 1] * y_factor


# --- Hoofdfunctie -----------------------------------------------------------

def lees_jcamp_tekst(tekst: str) -> Spectrum:
    """Zet de tekst van een JCAMP-DX-bestand om naar een ``Spectrum``.

    Bevat het bestand meerdere spectra, dan nemen we het eerste blok dat echt
    data bevat. Gooit ``JcampFout`` als er niets leesbaars in zit.
    """
    blokken = splits_in_blokken(tekst)
    gekozen = None
    for blok in blokken:
        labels, soort, dataregels = lees_labels(blok)
        if soort and dataregels:
            gekozen = (labels, soort, dataregels)
            break
    if gekozen is None:
        # Geen enkel blok met data: geef de kop van het eerste blok terug in de foutmelding.
        labels, soort, _ = lees_labels(blokken[0])
        if labels.get("NPOINTS", "").strip() == "0" or not soort:
            raise JcampFout("het bestand bevat geen datablok met meetpunten (##XYDATA, ##XYPOINTS of ##PEAK TABLE)")
        raise JcampFout("het datablok is leeg")

    labels, soort, dataregels = gekozen
    try:
        if soort == "XYDATA":
            x, y = _lees_xydata(dataregels, labels)
        else:
            x, y = _lees_xy_paren(dataregels, labels)
    except JcampFout:
        raise
    except (ValueError, OverflowError, IndexError) as fout:
        raise JcampFout(f"de getallen in het datablok zijn niet te lezen ({fout})") from fout

    npoints = _als_getal(labels, "NPOINTS")
    return Spectrum(
        titel=labels.get("TITLE", "").strip(),
        x=x,
        y=y,
        x_eenheid=labels.get("XUNITS", "").strip(),
        y_eenheid=labels.get("YUNITS", "").strip(),
        cas=labels.get("CAS REGISTRY NO", "").strip(),
        formule=" ".join(labels.get("MOLFORM", "").split()),
        toestand=labels.get("STATE", "").strip(),
        datablok_soort=soort,
        npoints_label=int(npoints) if npoints is not None else None,
        aantal_blokken=len(blokken),
        labels=labels,
    )


def decodeer_bytes(inhoud: bytes) -> str:
    """Zet de ruwe bytes van een bestand om naar tekst.

    De meeste bestanden zijn UTF-8 (of gewoon ASCII). Een klein deel van de
    NIST-bestanden gebruikt de oudere Latin-1-codering voor bijv. het
    graden-teken; daar vallen we op terug.
    """
    if inhoud.startswith(b"\xef\xbb\xbf"):      # UTF-8 "byte order mark" weghalen
        inhoud = inhoud[3:]
    try:
        return inhoud.decode("utf-8")
    except UnicodeDecodeError:
        return inhoud.decode("latin-1")


def lees_jcamp_bestand(pad) -> Spectrum:
    """Lees een JCAMP-DX-bestand van schijf."""
    with open(pad, "rb") as f:
        return lees_jcamp_tekst(decodeer_bytes(f.read()))
