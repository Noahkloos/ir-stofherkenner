"""Tests voor de functionele-groepenregels (het expertsysteem)."""

from __future__ import annotations

import pytest

from stofherkenner.functionele_groepen import REGELS, herken_functionele_groepen
from stofherkenner.jcamp_lezen import lees_jcamp_bestand
from stofherkenner.piekdetectie import Piek, detecteer_pieken
from stofherkenner.voorbewerking import RASTER, bewerk_voor


def piek(golfgetal: float, hoogte: float = 0.5, breedte: float = 20.0) -> Piek:
    return Piek(golfgetal=golfgetal, hoogte=hoogte, prominentie=hoogte, breedte=breedte)


def groepen(pieken) -> dict[str, str]:
    """Geef {groepnaam: zekerheid} voor een lijst pieken."""
    return {b.groep: b.zekerheid for b in herken_functionele_groepen(pieken)}


def bevindingen_van(pad):
    v = bewerk_voor(lees_jcamp_bestand(pad))
    return herken_functionele_groepen(detecteer_pieken(RASTER[v.masker], v.absorbantie[v.masker]))


def test_er_zijn_acht_regels():
    assert len(REGELS) == 8


def test_geen_pieken_geen_bevindingen():
    assert herken_functionele_groepen([]) == []
    # alleen C-H-pieken van een alkaan: geen van de acht groepen
    assert groepen([piek(2925, 1.0), piek(2855, 0.7), piek(1460, 0.3), piek(1378, 0.15)]) == {}


# --- Regels los, met zelfgekozen pieken --------------------------------------

def test_alcohol_vloeistof_brede_band():
    g = groepen([piek(3350, 0.8, breedte=250), piek(1050, 1.0), piek(2950, 0.6)])
    assert g["O–H (alcohol of fenol)"] == "hoog"


def test_alcohol_gasfase_smalle_vrije_oh():
    """Gasfase: smalle piek rond 3650 in plaats van de brede band uit het studieboek."""
    g = groepen([piek(3670, 0.18, breedte=40), piek(1060, 1.0), piek(2980, 0.9)])
    assert g["O–H (alcohol of fenol)"] == "hoog"


def test_smalle_piek_bij_3400_is_geen_alcohol():
    assert "O–H (alcohol of fenol)" not in groepen([piek(3400, 0.5, breedte=30), piek(2950, 1.0)])


def test_keton():
    g = groepen([piek(1715, 1.0), piek(2960, 0.3), piek(1360, 0.4)])
    assert g == {"C=O (keton of aldehyde)": "hoog"}


def test_aldehyde_krijgt_extra_reden():
    b = herken_functionele_groepen([piek(1730, 1.0), piek(2720, 0.1), piek(2820, 0.2)])
    keton = next(x for x in b if x.groep.startswith("C=O"))
    assert any("aldehyde" in r for r in keton.redenen)


def test_ester_vraagt_sterke_c_o_c_band():
    assert groepen([piek(1745, 0.8), piek(1240, 1.0), piek(1050, 0.4)])["Ester (–COO–)"] == "hoog"
    # C-O-C te zwak ten opzichte van C=O (zoals bij aceton): geen ester
    assert "Ester (–COO–)" not in groepen([piek(1742, 1.0), piek(1215, 0.55)])


def test_carbonzuur_vloeistof_en_gas():
    vloeistof = groepen([piek(1710, 1.0), piek(3000, 0.4, breedte=400), piek(2620, 0.12), piek(1290, 0.6)])
    assert vloeistof["Carbonzuur (–COOH)"] == "hoog"
    assert vloeistof["C=O (keton of aldehyde)"] == "laag"         # meta-regel: de C=O hoort bij het zuur
    gas = groepen([piek(1790, 1.0), piek(3580, 0.3, breedte=40), piek(1180, 0.6)])
    assert gas["Carbonzuur (–COOH)"] == "middel"


def test_nitril():
    assert groepen([piek(2230, 0.4, breedte=15)])["C≡N (nitril)"] == "hoog"
    assert "C≡N (nitril)" not in groepen([piek(2350, 0.4, breedte=15)])     # CO2 uit de lucht
    assert "C≡N (nitril)" not in groepen([piek(2120, 0.4, breedte=15)])     # alkyn


def test_primair_amine_twee_nh_pieken_plus_buiging():
    g = groepen([piek(3370, 0.3, 40), piek(3290, 0.3, 40), piek(1610, 0.3, 50), piek(2930, 1.0)])
    assert g["N–H (amine)"] == "middel"


def test_alkeen_zekerheid_hangt_af_van_steun():
    assert groepen([piek(1642, 0.1), piek(3080, 0.2), piek(912, 0.3)])["C=C (alkeen)"] == "hoog"
    assert groepen([piek(1642, 0.1), piek(3080, 0.2)])["C=C (alkeen)"] == "middel"
    assert groepen([piek(1642, 0.1)])["C=C (alkeen)"] == "laag"


def test_aromaat():
    g = groepen([piek(1600, 0.2), piek(1500, 0.4), piek(3040, 0.3), piek(735, 1.0)])
    assert g["Aromaat (benzeenring)"] == "hoog"
    # alleen een piek rond 1460 (CH2-buiging): geen aromaat
    assert "Aromaat (benzeenring)" not in groepen([piek(1460, 0.4), piek(2925, 1.0)])


def test_elke_bevinding_noemt_de_piek_als_reden():
    for b in herken_functionele_groepen([piek(1715, 1.0), piek(2230, 0.4, 15), piek(3350, 0.8, 250), piek(1050, 0.9)]):
        assert b.redenen, b.groep
        assert all("cm⁻¹" in r for r in b.redenen)
        assert b.zekerheid in ("hoog", "middel", "laag")


# --- Echte spectra: de verwachte groep wordt gevonden ------------------------

VERWACHT = [
    ("aceton_gas_C67641_IR_0.jdx", "C=O (keton of aldehyde)", ("hoog", "middel")),
    ("ethanol_gas_C64175_IR_0.jdx", "O–H (alcohol of fenol)", ("hoog", "middel")),
    ("ethanol_oplossing_C64175_IR_3.jdx", "O–H (alcohol of fenol)", ("hoog", "middel")),
    ("ethylacetaat_gas_C141786_IR_0.jdx", "Ester (–COO–)", ("hoog", "middel")),
    ("azijnzuur_oplossing_C64197_IR_2.jdx", "Carbonzuur (–COOH)", ("hoog", "middel")),
    ("benzonitril_vloeistof_micrometer_C100470_IR_1.jdx", "C≡N (nitril)", ("hoog",)),
    ("benzonitril_vloeistof_micrometer_C100470_IR_1.jdx", "Aromaat (benzeenring)", ("hoog", "middel")),
    ("1-hexeen_gas_C592416_IR_0.jdx", "C=C (alkeen)", ("hoog", "middel")),
    ("butylamine_vloeistof_C109739_IR_2.jdx", "N–H (amine)", ("hoog", "middel", "laag")),
    ("tolueen_vloeistof_C108883_IR_2.jdx", "Aromaat (benzeenring)", ("hoog", "middel")),
]


@pytest.mark.parametrize("bestand,groep,toegestaan", VERWACHT, ids=[f"{v[0].split('_C')[0]} -> {v[1]}" for v in VERWACHT])
def test_verwachte_groep_in_echt_spectrum(voorbeeldmap, bestand, groep, toegestaan):
    gevonden = {b.groep: b.zekerheid for b in bevindingen_van(voorbeeldmap / bestand)}
    assert groep in gevonden, f"{groep} niet gevonden; wel: {gevonden}"
    assert gevonden[groep] in toegestaan


# Groepen die er aantoonbaar NIET in zitten mogen niet met zekerheid 'hoog' of 'middel' gemeld worden
NIET_VERWACHT = [
    ("aceton_gas_C67641_IR_0.jdx", ["Ester (–COO–)", "O–H (alcohol of fenol)", "C≡N (nitril)", "Aromaat (benzeenring)"]),
    ("ethanol_gas_C64175_IR_0.jdx", ["C=O (keton of aldehyde)", "C≡N (nitril)", "Aromaat (benzeenring)"]),
    ("1-hexeen_gas_C592416_IR_0.jdx", ["C=O (keton of aldehyde)", "O–H (alcohol of fenol)", "C≡N (nitril)"]),
    ("tolueen_vloeistof_C108883_IR_2.jdx", ["C=O (keton of aldehyde)", "O–H (alcohol of fenol)", "C≡N (nitril)"]),
    ("butylamine_vloeistof_C109739_IR_2.jdx", ["C=O (keton of aldehyde)", "Aromaat (benzeenring)", "C≡N (nitril)"]),
]


@pytest.mark.parametrize("bestand,afwezig", NIET_VERWACHT, ids=[v[0].split("_C")[0] for v in NIET_VERWACHT])
def test_geen_stellige_valse_meldingen(voorbeeldmap, bestand, afwezig):
    gevonden = {b.groep: b.zekerheid for b in bevindingen_van(voorbeeldmap / bestand)}
    for groep in afwezig:
        assert gevonden.get(groep) not in ("hoog", "middel"), f"{groep} onterecht gemeld als {gevonden.get(groep)}"
