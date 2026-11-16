"""Tests voor de piekdetectie (LS, kwaliteitscriterium 3).

Deel 1: zelfgemaakte (synthetische) spectra waarvan we de piekposities exact
        kennen. Tolerantie: +/- 8 cm^-1 (twee rasterpunten).
Deel 2: echte NIST-spectra met bekende, kenmerkende pieken.
"""

from __future__ import annotations

import numpy as np
import pytest

from stofherkenner.jcamp_lezen import lees_jcamp_bestand
from stofherkenner.piekdetectie import detecteer_pieken, maak_glad, pieken_in_gebied, schat_ruis
from stofherkenner.voorbewerking import RASTER, bewerk_voor
from tests.conftest import gauss

TOLERANTIE = 8.0     # cm^-1


def gevonden_bij(pieken, golfgetal: float, tolerantie: float = TOLERANTIE) -> bool:
    return any(abs(p.golfgetal - golfgetal) <= tolerantie for p in pieken)


def synthetisch_spectrum(posities, hoogtes, breedtes, ruis: float, seed: int = 0) -> np.ndarray:
    """Maak een spectrum op het raster met Gauss-pieken op bekende plekken, plus willekeurige ruis."""
    rng = np.random.default_rng(seed)
    y = sum(gauss(RASTER, p, h, b) for p, h, b in zip(posities, hoogtes, breedtes))
    return y + rng.normal(0.0, ruis, RASTER.size)


# --- Deel 1: synthetische spectra -------------------------------------------

def test_vijf_bekende_pieken_worden_precies_gevonden():
    posities = [700.0, 1100.0, 1715.0, 2250.0, 2950.0]
    y = synthetisch_spectrum(posities, [0.5, 0.8, 1.0, 0.3, 0.6], [10, 15, 12, 8, 25], ruis=0.005)
    pieken = detecteer_pieken(RASTER, y)
    for positie in posities:
        assert gevonden_bij(pieken, positie), f"piek bij {positie} niet gevonden"
    assert len(pieken) == len(posities), f"er zijn nep-pieken gevonden: {[p.golfgetal for p in pieken]}"


@pytest.mark.parametrize("seed", range(10))
def test_willekeurige_piekposities(seed):
    """Tien spectra met elk zes pieken op willekeurige plekken (minstens 150 cm^-1 uit elkaar)."""
    rng = np.random.default_rng(seed)
    posities = np.sort(rng.choice(np.arange(650, 3700, 150), size=6, replace=False) + rng.uniform(-20, 20, 6))
    hoogtes = rng.uniform(0.2, 1.0, 6)
    breedtes = rng.uniform(8, 25, 6)
    pieken = detecteer_pieken(RASTER, synthetisch_spectrum(posities, hoogtes, breedtes, ruis=0.005, seed=seed))
    for positie in posities:
        assert gevonden_bij(pieken, positie), f"piek bij {positie:.0f} niet gevonden (seed {seed})"
    assert len(pieken) == 6


def test_alleen_ruis_geeft_geen_pieken():
    for seed in range(5):
        y = np.random.default_rng(seed).normal(0.0, 0.01, RASTER.size) + 0.5
        # een echt spectrum heeft altijd een piek; hier voegen we er een toe zodat "3% van de hoogste piek" betekenis heeft
        y += gauss(RASTER, 2000, 1.0, 15)
        pieken = detecteer_pieken(RASTER, y)
        assert len(pieken) == 1 and gevonden_bij(pieken, 2000)


def test_veel_ruis_piek_onder_de_ruis_wordt_niet_gemeld():
    """Een piek die kleiner is dan de ruis hoort NIET gevonden te worden; een grote wel."""
    y = synthetisch_spectrum([1000.0, 2000.0], [1.0, 0.03], [15, 15], ruis=0.03, seed=3)
    pieken = detecteer_pieken(RASTER, y)
    assert gevonden_bij(pieken, 1000)
    assert not gevonden_bij(pieken, 2000, tolerantie=30)


def test_losse_uitschieter_is_geen_piek():
    """Een 'spike' van een enkel punt (bijv. een storing) is te smal voor een echte band."""
    y = gauss(RASTER, 1500, 1.0, 15)
    y[400] += 0.5
    pieken = detecteer_pieken(RASTER, y)
    assert not gevonden_bij(pieken, RASTER[400], tolerantie=4)
    assert gevonden_bij(pieken, 1500)


def test_twee_overlappende_pieken_worden_los_gevonden():
    y = gauss(RASTER, 2850, 0.7, 12) + gauss(RASTER, 2925, 1.0, 12)
    pieken = detecteer_pieken(RASTER, y)
    assert gevonden_bij(pieken, 2850) and gevonden_bij(pieken, 2925)


def test_brede_band_wordt_als_breed_herkend():
    y = gauss(RASTER, 3350, 1.0, 110) + gauss(RASTER, 1050, 0.8, 12)
    pieken = detecteer_pieken(RASTER, y)
    breed = pieken_in_gebied(pieken, 3250, 3450)
    smal = pieken_in_gebied(pieken, 1000, 1100)
    assert breed and breed[0].is_breed and breed[0].breedte > 200
    assert smal and not smal[0].is_breed


def test_ruisschatting_met_mad_klopt_ongeveer():
    """De geschatte ruis moet in de buurt liggen van de ruis die we er zelf in gestopt hebben,
    ook als er grote pieken in het spectrum zitten (daarom MAD en geen gewone standaarddeviatie)."""
    for echte_ruis in (0.005, 0.02):
        y = synthetisch_spectrum([900, 1700, 2900], [1.0, 0.8, 0.6], [15, 12, 30], ruis=echte_ruis, seed=7)
        geschat = schat_ruis(y)
        assert 0.4 * echte_ruis < geschat < 1.6 * echte_ruis, (echte_ruis, geschat)
        assert np.std(y) > 5 * echte_ruis       # de gewone standaarddeviatie is veel te groot door de pieken


def test_gladmaken_behoudt_piekhoogte_en_vermindert_ruis():
    schoon = gauss(RASTER, 1700, 1.0, 15)
    met_ruis = schoon + np.random.default_rng(1).normal(0, 0.02, RASTER.size)
    glad = maak_glad(met_ruis)
    assert np.std(glad - schoon) < 0.7 * np.std(met_ruis - schoon)     # minder ruis
    assert glad.max() == pytest.approx(1.0, abs=0.06)                  # piekhoogte blijft behouden


def test_vlak_of_leeg_spectrum_geeft_lege_lijst():
    assert detecteer_pieken(RASTER, np.zeros(RASTER.size)) == []
    assert detecteer_pieken(RASTER[:3], np.array([0.0, 1.0, 0.0])) == []


# --- Deel 2: echte spectra met bekende pieken -------------------------------

# (bestand, omschrijving, ondergrens, bovengrens) - literatuurwaarden van kenmerkende banden
BEKENDE_PIEKEN = [
    ("aceton_gas_C67641_IR_0.jdx", "C=O-rek van aceton", 1700, 1760),
    ("aceton_gas_micrometer_C67641_IR_1.jdx", "C=O-rek van aceton (bestand in micrometer/transmissie)", 1700, 1760),
    ("ethanol_gas_C64175_IR_0.jdx", "vrije O-H-rek van ethanol in gasfase", 3600, 3700),
    ("ethanol_gas_C64175_IR_0.jdx", "C-O-rek van ethanol", 1030, 1090),
    ("ethanol_oplossing_C64175_IR_3.jdx", "brede O-H-rek van ethanol met waterstofbruggen", 3200, 3550),
    ("ethylacetaat_gas_C141786_IR_0.jdx", "C=O-rek van de ester", 1735, 1790),
    ("ethylacetaat_gas_C141786_IR_0.jdx", "C-O-C-rek van de ester", 1200, 1280),
    ("azijnzuur_oplossing_C64197_IR_2.jdx", "C=O-rek van het carbonzuur (dimeer)", 1690, 1730),
    ("benzonitril_vloeistof_micrometer_C100470_IR_1.jdx", "C≡N-rek van het nitril", 2210, 2250),
    ("1-hexeen_gas_C592416_IR_0.jdx", "C=C-rek van het alkeen", 1630, 1660),
    ("1-hexeen_gas_C592416_IR_0.jdx", "=C-H-rek boven 3000", 3060, 3100),
    ("butylamine_vloeistof_C109739_IR_2.jdx", "N-H-rek van het amine", 3250, 3400),
    ("tolueen_vloeistof_C108883_IR_2.jdx", "C-H-buiging van mono-gesubstitueerde benzeenring", 715, 745),
    ("tolueen_vloeistof_C108883_IR_2.jdx", "ringtrilling rond 1500", 1485, 1510),
]


@pytest.mark.parametrize("bestand,omschrijving,laag,hoog", BEKENDE_PIEKEN, ids=[f"{b[0].split('_C')[0]}: {b[1]}" for b in BEKENDE_PIEKEN])
def test_bekende_piek_in_echt_spectrum(voorbeeldmap, bestand, omschrijving, laag, hoog):
    voorbewerkt = bewerk_voor(lees_jcamp_bestand(voorbeeldmap / bestand))
    pieken = detecteer_pieken(RASTER[voorbewerkt.masker], voorbewerkt.absorbantie[voorbewerkt.masker])
    gevonden = pieken_in_gebied(pieken, laag, hoog)
    assert gevonden, f"{omschrijving}: geen piek tussen {laag} en {hoog}; wel gevonden: {[round(p.golfgetal) for p in pieken]}"


def test_co_van_aceton_is_de_hoogste_piek(voorbeeldmap):
    voorbewerkt = bewerk_voor(lees_jcamp_bestand(voorbeeldmap / "aceton_gas_C67641_IR_0.jdx"))
    pieken = detecteer_pieken(RASTER[voorbewerkt.masker], voorbewerkt.absorbantie[voorbewerkt.masker])
    hoogste = max(pieken, key=lambda p: p.hoogte)
    assert 1700 <= hoogste.golfgetal <= 1760
    assert 3 <= len(pieken) <= 15        # geen wildgroei aan ruispiekjes
