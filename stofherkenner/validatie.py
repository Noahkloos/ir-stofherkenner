"""Strenge controle van een geupload bestand.

Voordat de app iets met een bestand doet, controleren we stap voor stap of het
echt een geldig JCAMP-DX-bestand met een IR-spectrum is. Elke controle die
faalt levert een ``ValidatieFout`` op met twee stukjes Nederlandse tekst:

- ``wat_is_er_mis``: wat er precies fout is,
- ``wat_te_doen``:   wat de gebruiker kan doen om het op te lossen.

Zo crasht de app nooit op een kapot of kwaadaardig bestand, en weet de laborant
altijd wat de volgende stap is.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .jcamp_lezen import DATABLOK_LABELS, JcampFout, Spectrum, decodeer_bytes, lees_jcamp_tekst, lees_labels, splits_in_blokken
from .voorbewerking import herken_x_eenheid, herken_y_eenheid

MAX_BESTANDSGROOTTE = 5 * 1024 * 1024          # 5 MB
TOEGESTANE_EXTENSIES = (".jdx", ".dx")
VERPLICHTE_LABELS = ("TITLE", "JCAMP-DX", "XUNITS", "YUNITS")
MIN_AANTAL_PUNTEN = 2

# Bytes die in een normaal tekstbestand niet voorkomen (stuurtekens), behalve
# tab, nieuwe regel, "carriage return" en "form feed".
_STUURTEKENS = bytes(b for b in range(32) if b not in (9, 10, 12, 13)) + b"\x7f"

# Herkenbare beginnetjes van veelvoorkomende niet-tekstbestanden
_BEKENDE_BINAIRE_SOORTEN = {
    b"PK\x03\x04": "een zip-, Word- of Excel-bestand",
    b"%PDF": "een pdf-bestand",
    b"\x89PNG": "een png-afbeelding",
    b"\xff\xd8\xff": "een jpg-afbeelding",
    b"GIF8": "een gif-afbeelding",
    b"MZ": "een Windows-programma",
    b"\xd0\xcf\x11\xe0": "een oud Office-bestand",
}


class ValidatieFout(Exception):
    """Het bestand is afgekeurd. Bevat een uitleg en een advies in het Nederlands."""

    def __init__(self, code: str, wat_is_er_mis: str, wat_te_doen: str):
        super().__init__(f"{wat_is_er_mis} {wat_te_doen}")
        self.code = code                      # korte code, handig voor tests
        self.wat_is_er_mis = wat_is_er_mis
        self.wat_te_doen = wat_te_doen


@dataclass
class ValidatieResultaat:
    """Het resultaat van een geslaagde controle."""

    spectrum: Spectrum
    waarschuwingen: list[str] = field(default_factory=list)


# --- De losse controles (elk een kleine functie) ----------------------------

def controleer_extensie(bestandsnaam: str) -> None:
    """Controle 1: de bestandsnaam eindigt op .jdx of .dx (hoofdletters maken niet uit)."""
    if not bestandsnaam.lower().endswith(TOEGESTANE_EXTENSIES):
        extensie = "." + bestandsnaam.rsplit(".", 1)[-1] if "." in bestandsnaam else "(geen extensie)"
        raise ValidatieFout(
            "extensie",
            f"Het bestand '{bestandsnaam}' heeft de extensie {extensie}. "
            "De app accepteert alleen JCAMP-DX-bestanden (.jdx of .dx).",
            "Exporteer het spectrum in de software van je IR-spectrometer als JCAMP-DX "
            "(vaak onder 'Opslaan als' of 'Export') en upload dat bestand.",
        )


def controleer_grootte(inhoud: bytes) -> None:
    """Controle 2: niet leeg en niet groter dan 5 MB."""
    if len(inhoud) == 0:
        raise ValidatieFout(
            "leeg",
            "Het bestand is leeg (0 bytes).",
            "Exporteer het spectrum opnieuw uit de spectrometersoftware en upload het nieuwe bestand.",
        )
    if len(inhoud) > MAX_BESTANDSGROOTTE:
        raise ValidatieFout(
            "te_groot",
            f"Het bestand is {len(inhoud) / 1024 / 1024:.1f} MB. De maximale grootte is 5 MB.",
            "Exporteer het spectrum met een lagere resolutie of een kleiner golfgetalbereik "
            "(550-3800 cm⁻¹ is genoeg) en probeer het opnieuw.",
        )


def controleer_is_tekst(inhoud: bytes) -> None:
    """Controle 3: het is een tekstbestand en geen binair bestand (afbeelding, zip, programma...)."""
    for begin, soort in _BEKENDE_BINAIRE_SOORTEN.items():
        if inhoud.startswith(begin):
            raise ValidatieFout(
                "binair",
                f"Dit lijkt {soort} te zijn en geen JCAMP-DX-tekstbestand, ook al klopt de extensie.",
                "Upload het echte JCAMP-DX-bestand (een tekstbestand dat begint met ##TITLE=).",
            )
    # Tel de stuurtekens: bytes.translate verwijdert ze, het lengteverschil is het aantal.
    aantal_stuurtekens = len(inhoud) - len(inhoud.translate(None, _STUURTEKENS))
    if b"\x00" in inhoud or aantal_stuurtekens > 0.001 * len(inhoud):
        raise ValidatieFout(
            "binair",
            "Het bestand bevat binaire gegevens. Een JCAMP-DX-bestand is een gewoon tekstbestand.",
            "Controleer of je het juiste bestand hebt gekozen en exporteer het spectrum zo nodig "
            "opnieuw als JCAMP-DX (.jdx).",
        )


def controleer_structuur(tekst: str) -> None:
    """Controle 4: de verplichte labels, een datablok en ##END zijn aanwezig, in de goede volgorde."""
    eerste_regel = next((r.strip() for r in tekst.splitlines() if r.strip()), "")
    if not eerste_regel.startswith("##"):
        raise ValidatieFout(
            "geen_jcamp",
            "Het bestand begint niet met een JCAMP-DX-label (een regel die begint met ##, normaal ##TITLE=).",
            "Dit is geen JCAMP-DX-bestand. Exporteer het spectrum opnieuw als JCAMP-DX.",
        )
    if not eerste_regel.upper().replace(" ", "").startswith("##TITLE="):
        raise ValidatieFout(
            "ontbrekende_labels",
            "De eerste regel van een JCAMP-DX-bestand moet ##TITLE= zijn; dat is hier niet zo.",
            "Het bestand is beschadigd of onvolledig. Exporteer het spectrum opnieuw als JCAMP-DX.",
        )

    # We kijken naar het eerste blok dat een datablok heeft (of het eerste blok als er geen is).
    blokken = splits_in_blokken(tekst)
    labels, soort, dataregels = lees_labels(blokken[0])
    blok = blokken[0]
    for kandidaat in blokken:
        l, s, d = lees_labels(kandidaat)
        if s and d:
            labels, soort, dataregels, blok = l, s, d, kandidaat
            break

    ontbrekend = [f"##{naam}" for naam in VERPLICHTE_LABELS if naam not in labels]
    if not soort:
        ontbrekend.append("een datablok (##XYDATA, ##XYPOINTS of ##PEAK TABLE)")
    if "END" not in labels:
        ontbrekend.append("##END")
    if ontbrekend:
        raise ValidatieFout(
            "ontbrekende_labels",
            "Het bestand mist verplichte onderdelen van JCAMP-DX: " + ", ".join(ontbrekend) + ".",
            "Het bestand is waarschijnlijk afgekapt of met de hand bewerkt. Exporteer het spectrum "
            "opnieuw uit de spectrometersoftware.",
        )

    # ##END moet NA het datablok komen
    hoofdletters = blok.upper()
    positie_data = min(p for p in (hoofdletters.find("##" + naam) for naam in DATABLOK_LABELS) if p >= 0)
    if hoofdletters.rfind("##END") < positie_data:
        raise ValidatieFout(
            "ontbrekende_labels",
            "Het label ##END staat vóór het datablok; het datablok is dus niet netjes afgesloten.",
            "Het bestand is beschadigd. Exporteer het spectrum opnieuw als JCAMP-DX.",
        )

    if not labels.get("TITLE", "").strip():
        raise ValidatieFout(
            "ontbrekende_labels",
            "Het label ##TITLE is leeg.",
            "Geef het spectrum een naam in de spectrometersoftware en exporteer het opnieuw.",
        )
    if not dataregels:
        raise ValidatieFout(
            "geen_data",
            "Het datablok is leeg: er staan geen meetpunten in het bestand.",
            "Exporteer het spectrum opnieuw. (Sommige NIST-bestanden bevatten alleen een verwijzing "
            "naar een gescande afbeelding en geen meetpunten; die kun je niet gebruiken.)",
        )


def controleer_data(spectrum: Spectrum) -> list[str]:
    """Controle 5: de getallen zelf kloppen. Geeft eventuele waarschuwingen terug."""
    waarschuwingen: list[str] = []
    x, y = spectrum.x, spectrum.y

    if x.size < MIN_AANTAL_PUNTEN:
        raise ValidatieFout(
            "data_onleesbaar",
            f"Het datablok bevat maar {x.size} meetpunt(en); dat is geen spectrum.",
            "Exporteer het volledige spectrum opnieuw als JCAMP-DX.",
        )
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValidatieFout(
            "data_onleesbaar",
            "Het datablok bevat ongeldige getallen (NaN of oneindig).",
            "Exporteer het spectrum opnieuw uit de spectrometersoftware.",
        )
    if spectrum.npoints_label is not None and spectrum.npoints_label != x.size:
        raise ValidatieFout(
            "npoints",
            f"Volgens ##NPOINTS horen er {spectrum.npoints_label} meetpunten in het bestand te staan, "
            f"maar er zijn er {x.size} gevonden.",
            "Het bestand is waarschijnlijk afgekapt of beschadigd. Exporteer het spectrum opnieuw.",
        )
    if np.ptp(x) == 0:
        raise ValidatieFout(
            "data_onleesbaar",
            "Alle meetpunten hebben dezelfde x-waarde; dat is geen spectrum.",
            "Exporteer het spectrum opnieuw uit de spectrometersoftware.",
        )

    if herken_x_eenheid(spectrum.x_eenheid) is None:
        raise ValidatieFout(
            "eenheid",
            f"De eenheid van de x-as (##XUNITS={spectrum.x_eenheid}) wordt niet herkend.",
            "De app ondersteunt golfgetal (1/CM) en golflengte (MICROMETERS of NANOMETERS). "
            "Exporteer het spectrum met het golfgetal in cm⁻¹ op de x-as.",
        )
    if herken_y_eenheid(spectrum.y_eenheid) is None:
        raise ValidatieFout(
            "eenheid",
            f"De eenheid van de y-as (##YUNITS={spectrum.y_eenheid}) wordt niet ondersteund.",
            "De app ondersteunt transmissie (TRANSMITTANCE of %T) en absorbantie (ABSORBANCE). "
            "Exporteer het spectrum in een van die twee eenheden.",
        )

    if spectrum.aantal_blokken > 1:
        waarschuwingen.append(
            f"Het bestand bevat {spectrum.aantal_blokken} spectra; alleen het eerste spectrum met data wordt gebruikt."
        )
    if spectrum.npoints_label is None:
        waarschuwingen.append("Het label ##NPOINTS ontbreekt; het aantal meetpunten kon niet worden gecontroleerd.")
    return waarschuwingen


# --- Alles achter elkaar ----------------------------------------------------

def valideer_upload(bestandsnaam: str, inhoud: bytes) -> ValidatieResultaat:
    """Voer alle controles uit en geef het ingelezen spectrum terug.

    Gooit ``ValidatieFout`` bij het eerste probleem. Onverwachte fouten worden
    ook omgezet naar een ``ValidatieFout``: er lekt dus nooit een crash of een
    technische foutmelding naar de gebruiker.
    """
    try:
        controleer_extensie(bestandsnaam)
        controleer_grootte(inhoud)
        controleer_is_tekst(inhoud)
        tekst = decodeer_bytes(inhoud)
        controleer_structuur(tekst)
        try:
            spectrum = lees_jcamp_tekst(tekst)
        except JcampFout as fout:
            raise ValidatieFout(
                "data_onleesbaar",
                f"De meetgegevens in het bestand zijn niet te lezen: {fout}.",
                "Het bestand is beschadigd of geen echt JCAMP-DX-bestand. Exporteer het spectrum opnieuw.",
            ) from fout
        waarschuwingen = controleer_data(spectrum)
        return ValidatieResultaat(spectrum, waarschuwingen)
    except ValidatieFout:
        raise
    except Exception as fout:  # vangnet: wat er ook misgaat, de app mag niet crashen
        raise ValidatieFout(
            "onbekend",
            f"Het bestand kon niet worden verwerkt (onverwachte fout: {type(fout).__name__}).",
            "Controleer of het een geldig JCAMP-DX-bestand is en probeer het opnieuw.",
        ) from fout
