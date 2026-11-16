"""Bij elke piek: welke binding(en) kunnen deze piek veroorzaken?

Dit is een opzoektabel (correlatietabel): per golfgetalgebied staat welke
trilling van welke binding daar meestal een piek geeft. Voor een piek bij
1742 cm⁻¹ zoeken we alle gebieden waar 1742 in valt.

Belangrijk om te weten:
- De gebieden OVERLAPPEN. Een piek bij 1650 cm⁻¹ kan een C=C, een C=O van een
  amide of een N–H-buiging zijn. Daarom geven we "mogelijke bindingen", geen
  zeker antwoord.
- Onder ~1500 cm⁻¹ ligt het VINGERAFDRUKGEBIED (fingerprint): daar trillen
  hele stukken molecuul tegelijk en is een piek moeilijk aan één binding toe
  te wijzen. Dat zeggen we er dan ook eerlijk bij.
- Als een regel uit ``functionele_groepen.py`` deze piek als reden noemt,
  zetten we die uitleg bovenaan. Zo spreken de pieken-tabel en het paneel met
  functionele groepen elkaar niet tegen.

Bronnen: dezelfde correlatietabellen als functionele_groepen.py (Pavia e.a.;
Silverstein e.a.; Socrates), afgerond en voor gasfase iets verruimd.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .functionele_groepen import Bevinding
from .piekdetectie import Piek

GRENS_VINGERAFDRUK = 1500.0       # onder dit golfgetal: vingerafdrukgebied


@dataclass(frozen=True)
class Gebied:
    """Een regel uit de correlatietabel."""

    laag: float                   # ondergrens (cm⁻¹)
    hoog: float                   # bovengrens (cm⁻¹)
    binding: str                  # bijv. "C=O"
    omschrijving: str             # bijv. "rek, keton of aldehyde"
    min_breedte: float = 0.0      # alleen als de piek minstens zo breed is (cm⁻¹)
    max_breedte: float = 1e9      # alleen als de piek hooguit zo breed is (cm⁻¹)
    max_hoogte: float = 1e9       # alleen als de piek hooguit zo hoog is (relatief, hoogste piek = 1)


# De correlatietabel. Volgorde = volgorde in de tabel van de app (specifiek eerst).
CORRELATIETABEL: tuple[Gebied, ...] = (
    # --- X–H-rekken (boven 2500) ---
    Gebied(3580, 3700, "O–H", "vrije rek, alcohol of fenol (gasfase of verdund)", max_breedte=100),
    Gebied(3500, 3600, "O–H", "vrije rek, carbonzuur (gasfase)", max_breedte=100),
    Gebied(3200, 3550, "O–H", "rek met waterstofbruggen, alcohol of fenol (vloeistof/vast)", min_breedte=100),
    Gebied(3250, 3520, "N–H", "rek, amine of amide", max_breedte=300),
    Gebied(3260, 3330, "≡C–H", "rek, alkyn (scherp)", max_breedte=60),
    Gebied(2500, 3300, "O–H", "zeer brede rek, carbonzuur (dimeer)", min_breedte=250),
    Gebied(3010, 3110, "=C–H", "rek, alkeen of aromaat (boven 3000)"),
    Gebied(2840, 3010, "C–H", "rek, alkaan (CH₃, CH₂, CH; CH₃ naast C=O tot ~3010)"),
    Gebied(2680, 2860, "C–H", "rek, aldehyde (–CHO, vaak twee pieken rond 2720 en 2820)"),
    Gebied(2500, 2680, "O–H", "vleugel van de brede band van een carbonzuur"),
    Gebied(2550, 2600, "S–H", "rek, thiol (zwak)"),
    # --- drievoudige en cumulatieve bindingen ---
    Gebied(2330, 2370, "O=C=O", "CO₂ uit de lucht (meetartefact, geen stof in het monster)"),
    Gebied(2240, 2280, "N=C=O", "rek, isocyanaat"),
    Gebied(2205, 2265, "C≡N", "rek, nitril"),
    Gebied(2100, 2260, "C≡C", "rek, alkyn (vaak zwak)"),
    # --- dubbele bindingen (meest voorkomende eerst) ---
    Gebied(1660, 1780, "C=O", "rek, keton of aldehyde (gasfase tot ~1780)"),
    Gebied(1725, 1795, "C=O", "rek, ester (gasfase tot ~1790)"),
    Gebied(1680, 1730, "C=O", "rek, carbonzuur (dimeer)"),
    Gebied(1740, 1810, "C=O", "rek, carbonzuur (gasfase, monomeer)"),
    Gebied(1800, 1850, "C=O", "rek, zuuranhydride of acylchloride"),
    Gebied(1620, 1680, "C=C", "rek, alkeen"),
    Gebied(1630, 1690, "C=O", "rek, amide"),
    Gebied(1580, 1650, "N–H", "buiging, amine"),
    Gebied(1575, 1625, "C=C", "ringtrilling, aromaat (~1600)"),
    Gebied(1660, 2000, "C–H", "zwakke boventonen van een aromaat ('benzeenvingers')", max_hoogte=0.15),
    Gebied(1500, 1570, "NO₂", "asymmetrische rek, nitroverbinding"),
    # --- vingerafdrukgebied ---
    Gebied(1440, 1475, "C–H", "buiging, CH₂ en CH₃"),
    Gebied(1450, 1525, "C=C", "ringtrilling, aromaat (~1500)"),
    Gebied(1350, 1395, "C–H", "symmetrische buiging, CH₃"),
    Gebied(1300, 1440, "O–H", "buiging in het vlak, alcohol of carbonzuur"),
    Gebied(1330, 1390, "NO₂", "symmetrische rek, nitroverbinding"),
    Gebied(1150, 1300, "C–O–C", "rek, ester of ether"),
    Gebied(1000, 1260, "C–O", "rek, alcohol, ether, ester of zuur"),
    Gebied(1000, 1400, "C–F", "rek, fluorverbinding"),
    Gebied(880, 1000, "=C–H", "buiging uit het vlak, alkeen"),
    Gebied(675, 900, "C–H", "buiging uit het vlak, aromaat"),
    Gebied(650, 900, "N–H", "brede buiging uit het vlak (wag), amine", min_breedte=80),
    Gebied(600, 720, "O–H", "brede buiging uit het vlak, alcohol (vloeistof)", min_breedte=80),
    Gebied(600, 800, "C–Cl", "rek, chloorverbinding"),
)


def mogelijke_bindingen(piek: Piek, max_aantal: int = 4) -> list[str]:
    """Geef de mogelijke bindingen voor één piek, als korte teksten.

    Voorbeeld: piek bij 1742 cm⁻¹ -> ["C=O: rek, ester ...", "C=O: rek, keton of aldehyde ..."]
    """
    gevonden = [
        f"{g.binding}: {g.omschrijving}"
        for g in CORRELATIETABEL
        if g.laag <= piek.golfgetal <= g.hoog and g.min_breedte <= piek.breedte <= g.max_breedte
        and piek.hoogte <= g.max_hoogte
    ]
    return gevonden[:max_aantal]


# Een reden uit functionele_groepen.py ziet eruit als "C=O-rek: piek bij 1742 cm⁻¹"
_REDEN_PATROON = re.compile(r"^(?P<wat>.*): (?:piek|brede band) bij (?P<golfgetal>\d+) cm⁻¹$")


def regels_per_piek(bevindingen: list[Bevinding]) -> dict[int, list[str]]:
    """Welke regels uit het paneel 'functionele groepen' noemen welke piek?

    Geeft {afgerond golfgetal: ["Ester (–COO–): C=O-rek (ester)", ...]}.
    """
    per_piek: dict[int, list[str]] = {}
    for b in bevindingen:
        for reden in b.redenen:
            m = _REDEN_PATROON.match(reden)
            if m:
                per_piek.setdefault(int(m.group("golfgetal")), []).append(f"{b.groep}: {m.group('wat')} (zekerheid {b.zekerheid})")
    return per_piek


def piekentabel(pieken: list[Piek], bevindingen: list[Bevinding]) -> list[dict]:
    """Maak de tabel met alle pieken en hun mogelijke bindingen (een rij per piek, hoog -> laag golfgetal)."""
    volgens_regels = regels_per_piek(bevindingen)
    rijen = []
    for p in sorted(pieken, key=lambda p: -p.golfgetal):
        regels = volgens_regels.get(round(p.golfgetal), [])
        mogelijk = mogelijke_bindingen(p)
        if not mogelijk:
            mogelijk = ["geen standaardtoewijzing in de correlatietabel"]
        if p.golfgetal < GRENS_VINGERAFDRUK:
            mogelijk = mogelijk + ["(vingerafdrukgebied: toewijzing onzeker)"]
        rijen.append({
            "Golfgetal (cm⁻¹)": round(p.golfgetal),
            "Relatieve hoogte": round(p.hoogte, 2),
            "Breedte (cm⁻¹)": round(p.breedte),
            "Volgens de regels": "; ".join(regels) if regels else "–",
            "Mogelijke binding(en)": "; ".join(mogelijk),
        })
    return rijen
