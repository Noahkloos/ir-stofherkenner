"""Functionele groepen herkennen met vaste regels (een klein expertsysteem).

Dit is de UITLEGLAAG van de app. De regels beslissen niet welke stof het is
(dat doet de matching); ze vertellen alleen welke functionele groepen de
pieken doen vermoeden, zodat de laborant kan controleren of de top 5 logisch is.

Hoe werkt een regel?
    ALS er een piek ligt in gebied X (en eventueel ook een in gebied Y)
    DAN is groep Z waarschijnlijk aanwezig, met zekerheid hoog / middel / laag.
Elke conclusie noemt de pieken waarop hij gebaseerd is ("C=O: piek bij 1731 cm⁻¹").

GASFASE: ongeveer de helft van de NIST-spectra is in gasfase gemeten. Daar
ontbreken waterstofbruggen. Gevolgen waar de regels rekening mee houden:
- vrije O–H geeft een SMALLE piek rond 3580–3700 cm⁻¹, in plaats van de brede
  band rond 3200–3550 cm⁻¹ uit de studieboeken (vloeistof/vaste stof);
- C=O ligt in gas zo'n 15–30 cm⁻¹ HOGER dan in vloeistof;
- carbonzuren zijn in gas vaak losse moleculen (monomeer): C=O rond
  1760–1800 cm⁻¹ en een smalle O–H rond 3500–3600 cm⁻¹.

BRON van de golfgetalgebieden: standaard IR-correlatietabellen, zoals in
- D.L. Pavia, G.M. Lampman, G.S. Kriz, J.R. Vyvyan, "Introduction to
  Spectroscopy" (hoofdstuk Infrared Spectroscopy, correlatietabel);
- R.M. Silverstein, F.X. Webster, D.J. Kiemle, "Spectrometric Identification
  of Organic Compounds" (hoofdstuk Infrared Spectrometry);
- G. Socrates, "Infrared and Raman Characteristic Group Frequencies".
De gebieden zijn afgerond en waar nodig verruimd voor gasfase. Ze zijn door de
ontwikkelaar (met AI-hulp) opgesteld en met scripts/controle_functionele_groepen.py
getest op de NIST-bibliotheek; controleer ze voor gebruik in de praktijk tegen
je eigen studieboek.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .piekdetectie import Piek, pieken_in_gebied

BRONVERMELDING = (
    "Golfgetalgebieden gebaseerd op standaard IR-correlatietabellen (Pavia e.a., Introduction to "
    "Spectroscopy; Silverstein e.a., Spectrometric Identification of Organic Compounds; Socrates, "
    "Infrared and Raman Characteristic Group Frequencies), verruimd voor gasfasespectra."
)

# Hoe hoog moet een piek zijn (als deel van de hoogste piek) om "sterk" te heten?
STERK = 0.30
MIDDEL = 0.10


@dataclass
class Bevinding:
    """Een conclusie van een regel."""

    groep: str                         # bijv. "C=O (keton/aldehyde)"
    zekerheid: str                     # "hoog", "middel" of "laag"
    redenen: list[str] = field(default_factory=list)   # bijv. ["C=O-rek: piek bij 1731 cm⁻¹"]
    toelichting: str = ""              # extra uitleg of waarschuwing


# --- Kleine hulpfuncties ----------------------------------------------------

def _sterkste(pieken: list[Piek], laag: float, hoog: float, min_hoogte: float = 0.0,
              min_breedte: float = 0.0, max_breedte: float = 1e9) -> Piek | None:
    """De hoogste piek in een gebied die aan de eisen voor hoogte en breedte voldoet (of None)."""
    kandidaten = [
        p for p in pieken_in_gebied(pieken, laag, hoog)
        if p.hoogte >= min_hoogte and min_breedte <= p.breedte <= max_breedte
    ]
    return max(kandidaten, key=lambda p: p.hoogte) if kandidaten else None


def _reden(omschrijving: str, piek: Piek) -> str:
    """Maak een leesbare reden, bijv. 'C=O-rek: piek bij 1731 cm⁻¹'."""
    soort = "brede band" if piek.is_breed else "piek"
    return f"{omschrijving}: {soort} bij {piek.golfgetal:.0f} cm⁻¹"


# --- De regels (een functie per functionele groep) --------------------------

def regel_alcohol(pieken: list[Piek]) -> Bevinding | None:
    """O–H van een alcohol of fenol.

    Vloeistof/vast: brede, sterke band 3200–3550 (waterstofbruggen).
    Gas: smalle piek 3580–3700 (vrije O–H).
    Steun: C–O-rek, sterke piek 1000–1260.
    """
    breed = _sterkste(pieken, 3200, 3550, min_hoogte=MIDDEL, min_breedte=100)
    vrij = _sterkste(pieken, 3580, 3700, min_hoogte=0.03, max_breedte=100)
    c_o = _sterkste(pieken, 1000, 1260, min_hoogte=STERK)
    if not breed and not vrij:
        return None
    redenen = []
    if breed:
        redenen.append(_reden("O–H-rek met waterstofbruggen (vloeistof/vast)", breed))
    if vrij:
        redenen.append(_reden("vrije O–H-rek (gasfase of verdunde oplossing)", vrij))
    if c_o:
        redenen.append(_reden("C–O-rek", c_o))
    if c_o and (breed or (vrij and vrij.hoogte >= MIDDEL)):
        zekerheid = "hoog"
    elif c_o or breed:
        zekerheid = "middel"
    else:
        zekerheid = "laag"
    return Bevinding("O–H (alcohol of fenol)", zekerheid, redenen,
                     "Let op: water in het monster of in KBr geeft ook een brede band rond 3400 cm⁻¹; "
                     "N–H absorbeert in hetzelfde gebied.")


def regel_carbonzuur(pieken: list[Piek]) -> Bevinding | None:
    """Carbonzuur (–COOH): C=O en O–H samen.

    Vloeistof/vast (dimeer, twee zuurmoleculen aan elkaar via waterstofbruggen):
      C=O 1680–1730 + een zeer brede O–H-band van 2500 tot 3300. Die brede band
      herken je aan (a) een zeer brede piek, of (b) kleine piekjes op de
      "vleugel" bij 2500–2680, waar bijna niets anders absorbeert.
    Gas (monomeer, losse moleculen): C=O 1740–1810 + smalle O–H 3500–3600.
    """
    c_o_dimeer = _sterkste(pieken, 1680, 1730, min_hoogte=STERK)
    o_h_zeer_breed = _sterkste(pieken, 2500, 3300, min_hoogte=MIDDEL, min_breedte=250)
    o_h_vleugel = _sterkste(pieken, 2500, 2680, min_hoogte=0.05)
    c_o_gas = _sterkste(pieken, 1740, 1810, min_hoogte=STERK)
    o_h_gas = _sterkste(pieken, 3500, 3600, min_hoogte=0.05, max_breedte=100)
    c_o_enkel = _sterkste(pieken, 1050, 1320, min_hoogte=MIDDEL)

    if c_o_dimeer and (o_h_zeer_breed or o_h_vleugel):
        redenen = [_reden("C=O-rek (zuur, dimeer)", c_o_dimeer)]
        if o_h_zeer_breed:
            redenen.append(_reden("zeer brede O–H-rek van het zuur", o_h_zeer_breed))
        if o_h_vleugel:
            redenen.append(_reden("vleugel van de brede O–H-band van het zuur", o_h_vleugel))
        if c_o_enkel:
            redenen.append(_reden("C–O-rek", c_o_enkel))
        zekerheid = "hoog" if (o_h_zeer_breed and o_h_vleugel and c_o_enkel) else "middel"
        return Bevinding("Carbonzuur (–COOH)", zekerheid, redenen)
    if c_o_gas and o_h_gas:
        redenen = [_reden("C=O-rek (zuur in gasfase, monomeer)", c_o_gas),
                   _reden("vrije O–H-rek van het zuur (gasfase)", o_h_gas)]
        if c_o_enkel:
            redenen.append(_reden("C–O-rek", c_o_enkel))
        return Bevinding("Carbonzuur (–COOH)", "middel", redenen,
                         "Gasfase: zuren zijn dan losse moleculen, waardoor de C=O hoger ligt en de O–H smal is.")
    return None


def regel_ester(pieken: list[Piek]) -> Bevinding | None:
    """Ester: C=O 1730–1750 (gas tot ~1790) + sterke C–O–C-rek 1150–1300.

    Kenmerkend voor een ester is dat de C–O–C-band ongeveer EVEN STERK is als
    de C=O-band (vaak zelfs sterker). Een keton zoals aceton heeft ook een band
    rond 1220 cm⁻¹, maar die is duidelijk zwakker dan zijn C=O. Daarom eisen we
    dat de C–O–C-band minstens 70% van de hoogte van de C=O-band heeft.
    """
    c_dubbel_o = _sterkste(pieken, 1725, 1795, min_hoogte=STERK)
    c_o_c = _sterkste(pieken, 1150, 1300, min_hoogte=STERK)
    if not (c_dubbel_o and c_o_c):
        return None
    verhouding = c_o_c.hoogte / c_dubbel_o.hoogte
    if verhouding < 0.7:
        return None
    redenen = [_reden("C=O-rek (ester)", c_dubbel_o),
               _reden(f"C–O–C-rek ({verhouding:.0%} van de hoogte van de C=O-piek)", c_o_c)]
    tweede = _sterkste(pieken, 1000, 1150, min_hoogte=MIDDEL)
    if tweede:
        redenen.append(_reden("tweede C–O-rek", tweede))
    zekerheid = "hoog" if verhouding >= 0.9 and tweede else "middel"
    return Bevinding("Ester (–COO–)", zekerheid, redenen,
                     "Een keton of aldehyde naast een ether of alcohol kan hetzelfde patroon geven.")


def regel_keton_aldehyde(pieken: list[Piek]) -> Bevinding | None:
    """C=O van keton of aldehyde: sterke piek 1680–1750 (gas tot ~1780).

    Aanwijzing voor een aldehyde: C–H-rek van de aldehydegroep rond 2700–2850
    (vaak twee pieken, bij ~2720 en ~2820).
    """
    c_dubbel_o = _sterkste(pieken, 1660, 1780, min_hoogte=STERK)
    if not c_dubbel_o:
        return None
    redenen = [_reden("C=O-rek", c_dubbel_o)]
    aldehyde_ch = _sterkste(pieken, 2680, 2760, min_hoogte=0.03)
    toelichting = "Een C=O-piek alleen onderscheidt keton, aldehyde, ester en zuur niet; kijk ook naar de andere regels."
    if aldehyde_ch:
        redenen.append(_reden("C–H-rek van een aldehyde (–CHO)", aldehyde_ch))
        toelichting = "De extra piek rond 2720 cm⁻¹ wijst op een aldehyde. " + toelichting
    zekerheid = "hoog" if c_dubbel_o.hoogte >= 0.5 else "middel"
    return Bevinding("C=O (keton of aldehyde)", zekerheid, redenen, toelichting)


def regel_amine(pieken: list[Piek]) -> Bevinding | None:
    """N–H van een amine: 3300–3500 (primair: twee pieken; secundair: een, zwak) + N–H-buiging 1580–1650."""
    n_h = [p for p in pieken_in_gebied(pieken, 3250, 3520) if p.hoogte >= 0.03 and p.breedte < 300]
    if not n_h:
        return None
    buiging = _sterkste(pieken, 1580, 1650, min_hoogte=0.05)
    smal = [p for p in n_h if p.breedte < 100]
    if not buiging and not smal:
        return None                    # alleen een brede band zonder N–H-buiging: eerder O–H dan N–H
    redenen = [_reden("N–H-rek", p) for p in n_h[:2]]
    if buiging:
        redenen.append(_reden("N–H-buiging", buiging))
    if len(n_h) >= 2 and buiging:
        zekerheid, soort = "middel", "twee N–H-pieken: waarschijnlijk een primair amine (–NH₂)."
    elif buiging or len(n_h) >= 2:
        zekerheid, soort = "laag", "mogelijk een primair of secundair amine."
    else:
        zekerheid, soort = "laag", "één smalle piek: mogelijk een secundair amine (–NH–)."
    return Bevinding("N–H (amine)", zekerheid, redenen,
                     soort.capitalize() + " Let op: O–H (alcohol, water) en amiden absorberen in hetzelfde gebied; "
                     "in gasfase zijn N–H-pieken vaak zwak.")


def regel_nitril(pieken: list[Piek]) -> Bevinding | None:
    """C≡N van een nitril: scherpe piek 2210–2260. Dit gebied is verder bijna leeg."""
    c_n = _sterkste(pieken, 2205, 2265, min_hoogte=0.03, max_breedte=80)
    if not c_n:
        return None
    zekerheid = "hoog" if c_n.hoogte >= MIDDEL else "middel"
    return Bevinding("C≡N (nitril)", zekerheid, [_reden("C≡N-rek", c_n)],
                     "Alkynen (C≡C, 2100–2260 cm⁻¹) en isocyanaten (~2270 cm⁻¹) liggen dichtbij. "
                     "CO₂ uit de lucht geeft een piek rond 2350 cm⁻¹; dat is geen nitril.")


def regel_alkeen(pieken: list[Piek]) -> Bevinding | None:
    """C=C van een alkeen: C=C-rek 1620–1680 (zwak tot middel) + =C–H-rek 3010–3100 + =C–H-buiging 880–1000."""
    c_c = _sterkste(pieken, 1620, 1680, min_hoogte=0.03, max_breedte=80)
    c_h_rek = _sterkste(pieken, 3010, 3100, min_hoogte=0.03)
    c_h_buiging = _sterkste(pieken, 880, 1000, min_hoogte=MIDDEL)
    if not c_c:
        return None
    redenen = [_reden("C=C-rek", c_c)]
    if c_h_rek:
        redenen.append(_reden("=C–H-rek (boven 3000 cm⁻¹)", c_h_rek))
    if c_h_buiging:
        redenen.append(_reden("=C–H-buiging (uit het vlak)", c_h_buiging))
    steun = sum(x is not None for x in (c_h_rek, c_h_buiging))
    zekerheid = {2: "hoog", 1: "middel", 0: "laag"}[steun]
    return Bevinding("C=C (alkeen)", zekerheid, redenen,
                     "Een C=O of N–H-buiging vlak in de buurt kan deze zwakke piek verstoren; "
                     "symmetrische alkenen geven bijna geen C=C-piek.")


def regel_aromaat(pieken: list[Piek]) -> Bevinding | None:
    """Aromatische ring: ringtrillingen bij ~1600 en ~1500 + aromatische C–H-rek 3000–3100 + sterke C–H-buiging 675–900."""
    # Ringtrillingen en C–H-buigingen van een aromaat zijn SCHERPE pieken; een brede
    # band in hetzelfde gebied (bijv. N–H van een amine) telt daarom niet mee.
    ring_1600 = _sterkste(pieken, 1575, 1625, min_hoogte=0.03, max_breedte=70)
    ring_1500 = _sterkste(pieken, 1450, 1525, min_hoogte=0.05, max_breedte=70)
    c_h_rek = _sterkste(pieken, 3000, 3110, min_hoogte=0.02)
    c_h_buiging = _sterkste(pieken, 675, 900, min_hoogte=STERK, max_breedte=70)
    if not (ring_1500 and (ring_1600 or c_h_buiging)):
        return None
    redenen = []
    if ring_1600:
        redenen.append(_reden("ringtrilling C=C (~1600)", ring_1600))
    redenen.append(_reden("ringtrilling C=C (~1500)", ring_1500))
    if c_h_rek:
        redenen.append(_reden("aromatische C–H-rek (boven 3000 cm⁻¹)", c_h_rek))
    if c_h_buiging:
        redenen.append(_reden("C–H-buiging uit het vlak", c_h_buiging))
    steun = sum(x is not None for x in (ring_1600, c_h_rek, c_h_buiging))
    if steun < 2:
        return None                    # te weinig aanwijzingen: 1450–1525 alleen kan ook CH2/CH3 zijn
    zekerheid = "hoog" if steun == 3 else "middel"
    return Bevinding("Aromaat (benzeenring)", zekerheid, redenen,
                     "De positie van de sterke piek tussen 675 en 900 cm⁻¹ zegt iets over het substitutiepatroon.")


# Volgorde = volgorde waarin de app de groepen toont
REGELS = (
    regel_alcohol,
    regel_carbonzuur,
    regel_keton_aldehyde,
    regel_ester,
    regel_amine,
    regel_nitril,
    regel_alkeen,
    regel_aromaat,
)


def herken_functionele_groepen(pieken: list[Piek]) -> list[Bevinding]:
    """Pas alle regels toe op de gevonden pieken en geef de bevindingen terug.

    De piekhoogtes moeten genormaliseerd zijn (hoogste piek = 1), zoals na
    ``voorbewerking.bewerk_voor``.

    Drie regels over samenhang ("meta-regels"):
    - Is er een carbonzuur gevonden, dan is de losse melding "O–H (alcohol)"
      minder zeker: de O–H hoort dan waarschijnlijk bij het zuur.
    - Is er een ester (zekerheid hoog) of carbonzuur gevonden, dan wordt de
      algemene melding "C=O (keton of aldehyde)" minder zeker.
    - Wijst alles op een primair amine en ontbreekt een sterke C–O-piek, dan
      is de brede band rond 3300 cm⁻¹ eerder N–H dan O–H.
    """
    bevindingen = [b for b in (regel(pieken) for regel in REGELS) if b is not None]
    groepen = {b.groep: b for b in bevindingen}
    zuur = groepen.get("Carbonzuur (–COOH)")
    ester = groepen.get("Ester (–COO–)")
    alcohol = groepen.get("O–H (alcohol of fenol)")
    keton = groepen.get("C=O (keton of aldehyde)")
    if zuur and alcohol:
        alcohol.zekerheid = "laag"
        alcohol.toelichting = "De O–H hoort waarschijnlijk bij het carbonzuur. " + alcohol.toelichting
    if keton and (zuur or ester):
        andere = " of ".join(n for n, b in (("een carbonzuur", zuur), ("een ester", ester)) if b)
        if zuur or ester.zekerheid == "hoog":
            keton.zekerheid = "laag"
        keton.toelichting = f"De C=O-piek past ook bij {andere} (zie die regel). " + keton.toelichting
    amine = groepen.get("N–H (amine)")
    sterke_c_o = any("C–O-rek" in r for r in alcohol.redenen) if alcohol else False
    if alcohol and amine and amine.zekerheid == "middel" and not sterke_c_o:
        alcohol.zekerheid = "laag"
        alcohol.toelichting = ("Er is geen sterke C–O-piek en het patroon past bij een amine; de band rond "
                               "3300 cm⁻¹ is dan eerder N–H dan O–H. " + alcohol.toelichting)
    return bevindingen
