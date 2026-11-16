"""Bij elke piek: welke trilling van welke binding kan deze piek veroorzaken?

Dit is een opzoektabel (correlatietabel): per golfgetalgebied staat welke
trilling van welke binding daar meestal een piek geeft. Voor een piek bij
1742 cm⁻¹ zoeken we alle gebieden waar 1742 in valt.

De trillingen staan in de gebruikelijke IR-notatie:
    ν = strekvibratie, δ = buigvibratie (in het vlak),
    γ = buigvibratie uit het vlak, ω = wagging (kwispelen).
Voorbeeld: "ν(C=O) – keton of aldehyde" = de C=O-strekvibratie van een keton of aldehyde.

Belangrijk om te weten:
- De gebieden OVERLAPPEN. Een piek bij 1650 cm⁻¹ kan een C=C, een C=O van een
  amide of een N–H-buiging zijn. Daarom geven we "mogelijke toewijzingen",
  geen zeker antwoord.
- Onder ~1500 cm⁻¹ ligt het VINGERAFDRUKGEBIED (fingerprint): daar trillen
  hele stukken molecuul tegelijk en is een piek moeilijk aan één binding toe
  te wijzen. Dat zeggen we er dan ook eerlijk bij.
- Als een regel uit ``functionele_groepen.py`` deze piek als reden noemt, tonen
  we dat in een aparte kolom. Zo spreken de piekentabel en het paneel met
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

# Uitleg van de notatie, zoals in IR-literatuur gebruikelijk
VERKLARING_NOTATIE = ("ν = strekvibratie · δ = buigvibratie (in het vlak) · γ = buigvibratie uit het vlak · "
                      "ω = wagging (kwispelen)")

# Indeling van de intensiteit (relatieve hoogte, hoogste piek = 1) en de bandvorm, zoals in IR-tabellen (s/m/w)
GRENS_STERK = 0.50
GRENS_MIDDEL = 0.15
GRENS_BREED = 100.0               # cm⁻¹ breedte op halve hoogte


@dataclass(frozen=True)
class Gebied:
    """Een regel uit de correlatietabel."""

    laag: float                   # ondergrens (cm⁻¹)
    hoog: float                   # bovengrens (cm⁻¹)
    trilling: str                 # in IR-notatie, bijv. "ν(C=O)"
    groep: str                    # bij welke stofgroep, bijv. "keton of aldehyde"
    min_breedte: float = 0.0      # alleen als de piek minstens zo breed is (cm⁻¹)
    max_breedte: float = 1e9      # alleen als de piek hooguit zo breed is (cm⁻¹)
    max_hoogte: float = 1e9       # alleen als de piek hooguit zo hoog is (relatief, hoogste piek = 1)

    @property
    def tekst(self) -> str:
        return f"{self.trilling} – {self.groep}"


# De correlatietabel. Volgorde = volgorde in de app (meest voorkomende toewijzing eerst).
CORRELATIETABEL: tuple[Gebied, ...] = (
    # --- X–H-strekvibraties (boven 2500 cm⁻¹) ---
    Gebied(3580, 3700, "ν(O–H), vrij", "alcohol of fenol (gasfase of verdund)", max_breedte=100),
    Gebied(3500, 3600, "ν(O–H), vrij", "carbonzuur (gasfase)", max_breedte=100),
    Gebied(3200, 3550, "ν(O–H), waterstofbrug", "alcohol of fenol (vloeistof/vast)", min_breedte=100),
    Gebied(3250, 3520, "ν(N–H)", "amine of amide", max_breedte=300),
    Gebied(3260, 3330, "ν(≡C–H)", "alkyn (scherp)", max_breedte=60),
    Gebied(2500, 3300, "ν(O–H), zeer breed", "carbonzuur (dimeer)", min_breedte=250),
    Gebied(3010, 3110, "ν(=C–H)", "alkeen of aromaat"),
    Gebied(2840, 3010, "ν(C–H)", "alkylgroep (CH₃, CH₂, CH)"),
    Gebied(2680, 2860, "ν(C–H)", "aldehyde (–CHO; vaak twee banden bij ~2720 en ~2820)"),
    Gebied(2500, 2680, "ν(O–H)", "flank van de brede carbonzuurband"),
    Gebied(2550, 2600, "ν(S–H)", "thiol (zwak)"),
    # --- drievoudige en cumulatieve bindingen ---
    Gebied(2330, 2370, "ν(O=C=O)", "CO₂ uit de lucht – meetartefact, geen bestanddeel van het monster"),
    Gebied(2240, 2280, "ν(N=C=O)", "isocyanaat"),
    Gebied(2205, 2265, "ν(C≡N)", "nitril"),
    Gebied(2100, 2260, "ν(C≡C)", "alkyn (vaak zwak)"),
    # --- dubbele bindingen (meest voorkomende eerst) ---
    Gebied(1660, 1780, "ν(C=O)", "keton of aldehyde (gasfase tot ~1780)"),
    Gebied(1725, 1795, "ν(C=O)", "ester (gasfase tot ~1790)"),
    Gebied(1680, 1730, "ν(C=O)", "carbonzuur (dimeer)"),
    Gebied(1740, 1810, "ν(C=O)", "carbonzuur (gasfase, monomeer)"),
    Gebied(1800, 1850, "ν(C=O)", "zuuranhydride of acylchloride"),
    Gebied(1620, 1680, "ν(C=C)", "alkeen"),
    Gebied(1630, 1690, "ν(C=O)", "amide (amide-I-band)"),
    Gebied(1575, 1625, "ν(C=C)", "aromatische ring (~1600)"),
    Gebied(1580, 1650, "δ(N–H)", "primair amine"),
    Gebied(1660, 2000, "boventonen", "aromaat (zwakke 'benzeenvingers')", max_hoogte=0.15),
    Gebied(1475, 1525, "ν(C=C)", "aromatische ring (~1500)"),
    Gebied(1500, 1570, "ν(NO₂), asymm.", "nitroverbinding"),
    # --- vingerafdrukgebied (onder 1500 cm⁻¹) ---
    Gebied(1440, 1475, "δ(CH₂/CH₃)", "alkylgroep"),
    Gebied(1450, 1475, "ν(C=C)", "aromatische ring (~1450)"),
    Gebied(1350, 1395, "δ(CH₃), symm.", "methylgroep"),
    Gebied(1300, 1440, "δ(O–H)", "alcohol of carbonzuur"),
    Gebied(1330, 1390, "ν(NO₂), symm.", "nitroverbinding"),
    Gebied(1150, 1300, "ν(C–O–C)", "ester of ether"),
    Gebied(1000, 1320, "ν(C–O)", "alcohol, ether, ester of carbonzuur"),
    Gebied(1000, 1400, "ν(C–F)", "fluorverbinding"),
    Gebied(880, 1000, "γ(=C–H)", "alkeen"),
    Gebied(675, 900, "γ(C–H)", "aromaat (substitutiepatroon)"),
    Gebied(650, 900, "ω(N–H)", "amine (brede band)", min_breedte=80),
    Gebied(600, 720, "γ(O–H)", "alcohol (brede band, vloeistof)", min_breedte=80),
    Gebied(600, 800, "ν(C–Cl)", "chloorverbinding"),
)


def mogelijke_bindingen(piek: Piek, max_aantal: int = 4) -> list[str]:
    """Geef de mogelijke toewijzingen voor één piek, als korte teksten in IR-notatie.

    Voorbeeld: piek bij 1742 cm⁻¹ -> ["ν(C=O) – keton of aldehyde ...", "ν(C=O) – ester ...", ...]
    """
    gevonden = [
        g.tekst
        for g in CORRELATIETABEL
        if g.laag <= piek.golfgetal <= g.hoog and g.min_breedte <= piek.breedte <= g.max_breedte
        and piek.hoogte <= g.max_hoogte
    ]
    return gevonden[:max_aantal]


def intensiteitsklasse(hoogte: float) -> str:
    """Sterk / middel / zwak, zoals in IR-tabellen (s / m / w)."""
    if hoogte >= GRENS_STERK:
        return "sterk"
    if hoogte >= GRENS_MIDDEL:
        return "middel"
    return "zwak"


# Een reden uit functionele_groepen.py ziet eruit als "C=O-rek: piek bij 1742 cm⁻¹"
_REDEN_PATROON = re.compile(r"^(?P<wat>.*): (?:piek|brede band) bij (?P<golfgetal>\d+) cm⁻¹$")


@dataclass(frozen=True)
class RegelToewijzing:
    """Een regel uit het paneel met functionele groepen die deze piek gebruikt."""

    groep: str          # bijv. "Ester (–COO–)"
    kenmerk: str        # bijv. "C=O-rek (ester)"
    zekerheid: str      # "hoog", "middel" of "laag"

    @property
    def tekst(self) -> str:
        return f"{self.groep}: {self.kenmerk} (zekerheid {self.zekerheid})"


def regels_per_piek(bevindingen: list[Bevinding]) -> dict[int, list[RegelToewijzing]]:
    """Welke regels uit het paneel 'functionele groepen' noemen welke piek? {afgerond golfgetal: [...]}"""
    per_piek: dict[int, list[RegelToewijzing]] = {}
    for b in bevindingen:
        for reden in b.redenen:
            m = _REDEN_PATROON.match(reden)
            if m:
                per_piek.setdefault(int(m.group("golfgetal")), []).append(
                    RegelToewijzing(b.groep, m.group("wat"), b.zekerheid))
    return per_piek


@dataclass
class PiekRij:
    """Alles wat de app over één piek laat zien."""

    golfgetal: int
    hoogte: float
    intensiteit: str                    # sterk / middel / zwak
    breedte: int
    bandvorm: str                       # scherp / breed
    regels: list[RegelToewijzing]
    toewijzingen: list[str]             # uit de correlatietabel
    vingerafdruk: bool                  # onder 1500 cm⁻¹

    def als_dict(self) -> dict:
        """Platte versie (tekst per kolom), bijv. voor een tabel of een csv."""
        return {
            "Golfgetal (cm⁻¹)": self.golfgetal,
            "Intensiteit": f"{self.intensiteit} ({self.hoogte:.2f})",
            "Bandvorm": f"{self.bandvorm} ({self.breedte} cm⁻¹)",
            "Toewijzing door de regels": "; ".join(r.tekst for r in self.regels) or "–",
            "Mogelijke toewijzingen": "; ".join(self.toewijzingen) or "geen standaardtoewijzing",
        }


def piekentabel(pieken: list[Piek], bevindingen: list[Bevinding]) -> list[PiekRij]:
    """Een rij per piek, van hoog naar laag golfgetal (zoals de x-as van een IR-spectrum)."""
    volgens_regels = regels_per_piek(bevindingen)
    rijen = []
    for p in sorted(pieken, key=lambda p: -p.golfgetal):
        rijen.append(PiekRij(
            golfgetal=round(p.golfgetal),
            hoogte=float(p.hoogte),
            intensiteit=intensiteitsklasse(p.hoogte),
            breedte=round(p.breedte),
            bandvorm="breed" if p.breedte >= GRENS_BREED else "scherp",
            regels=volgens_regels.get(round(p.golfgetal), []),
            toewijzingen=mogelijke_bindingen(p),
            vingerafdruk=p.golfgetal < GRENS_VINGERAFDRUK,
        ))
    return rijen
