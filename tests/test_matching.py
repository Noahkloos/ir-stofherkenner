"""Tests voor de matching (cosinus, Pearson, Euclidisch) en de zoekfunctie."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from stofherkenner.jcamp_lezen import lees_jcamp_bestand
from stofherkenner.matching import METHODEN, beoordeel_resultaat, bereken_scores, maak_bibliotheek, zoek
from stofherkenner.voorbewerking import RASTER, bewerk_voor, normaliseer
from tests.conftest import gauss

VOL = np.ones(RASTER.size, dtype=bool)


def spectrum(*pieken) -> np.ndarray:
    """Genormaliseerd spectrum met Gauss-pieken: spectrum((1700, 1.0, 15), (2950, 0.5, 20))."""
    return normaliseer(sum(gauss(RASTER, p, h, b) for p, h, b in pieken), VOL)


def mini_bibliotheek():
    """Vier 'stoffen'; stof A heeft twee spectra."""
    spectra = np.vstack([
        spectrum((1715, 1.0, 15), (1220, 0.6, 15), (2960, 0.3, 25)),      # A-1  "keton"
        spectrum((1718, 1.0, 16), (1222, 0.55, 15), (2962, 0.35, 25)),    # A-2  zelfde stof, iets andere meting
        spectrum((3350, 0.8, 100), (1050, 1.0, 15), (2950, 0.6, 25)),     # B    "alcohol"
        spectrum((2230, 0.5, 8), (1500, 0.7, 8), (750, 1.0, 10)),         # C    "aromatisch nitril"
        spectrum((2925, 1.0, 20), (2855, 0.7, 15), (1460, 0.3, 12)),      # D    "alkaan"
    ]).astype(np.float32)
    meta = pd.DataFrame({
        "nist_id": ["A", "A", "B", "C", "D"],
        "naam": ["stof A", "stof A", "stof B", "stof C", "stof D"],
        "cas": ["1-00-0", "1-00-0", "2-00-0", "3-00-0", ""],
        "formule": ["C3H6O", "C3H6O", "C2H6O", "C7H5N", "C6H14"],
        "fase": ["gas", "vloeistof", "vloeistof", "vloeistof", "gas"],
        "bestand": ["A_IR_0.jdx", "A_IR_1.jdx", "B_IR_0.jdx", "C_IR_0.jdx", "D_IR_0.jdx"],
    })
    maskers = np.ones_like(spectra, dtype=np.float32)
    return maak_bibliotheek(spectra, maskers, meta, RASTER)


# --- De rekenregels zelf -----------------------------------------------------

def scores(a, b, methode, masker_a=VOL, masker_b=VOL) -> float:
    b2 = np.atleast_2d(b).astype(np.float32)
    mb = np.atleast_2d(masker_b).astype(np.float32)
    return float(bereken_scores(b2, mb, b2 * b2, a, masker_a, methode)[0, 0])


@pytest.mark.parametrize("methode", METHODEN)
def test_identiek_spectrum_scoort_100(methode):
    a = spectrum((1700, 1.0, 15), (2950, 0.5, 20)) - 0.3       # vectoren mogen negatief zijn (afgeleide)
    assert scores(a, a, methode) == pytest.approx(100.0, abs=0.01)


def test_cosinus_en_pearson_negeren_schaal_euclidisch_niet():
    a = spectrum((1700, 1.0, 15), (2950, 0.5, 20))
    assert scores(a, 0.3 * a, "cosinus") == pytest.approx(100.0, abs=0.01)
    assert scores(a, 0.3 * a, "pearson") == pytest.approx(100.0, abs=0.01)
    assert scores(a, 0.3 * a, "euclidisch") < 99.0


def test_pearson_negeert_constante_verschuiving_cosinus_niet():
    a = spectrum((1700, 1.0, 15), (2950, 0.5, 20))
    assert scores(a, a + 0.5, "pearson") == pytest.approx(100.0, abs=0.01)
    assert scores(a, a + 0.5, "cosinus") < 90.0


def test_niet_overlappende_pieken_scoren_laag():
    a, b = spectrum((1000, 1.0, 10)), spectrum((3000, 1.0, 10))
    assert scores(a, b, "cosinus") < 1.0
    assert scores(a, b, "pearson") < 1.0


def test_handmatig_nagerekend_voorbeeld():
    """Klein voorbeeld dat je met de hand kunt narekenen (zie docs/theorie_matching.md).

    a = (1, 2, 3, 0, ...)   b = (2, 2, 1, 0, ...)
    cosinus    = (1*2 + 2*2 + 3*1) / (wortel(14) * wortel(9)) = 9 / 11,225 = 0,8018
    """
    a = np.zeros(RASTER.size)
    b = np.zeros(RASTER.size)
    a[:3], b[:3] = [1, 2, 3], [2, 2, 1]
    assert scores(a, b, "cosinus") == pytest.approx(80.18, abs=0.01)
    # Euclidisch: afstand^2 = 1 + 0 + 4 = 5; RMS over 813 punten = wortel(5/813) = 0,0784 -> score 92,16
    assert scores(a, b, "euclidisch") == pytest.approx(100 * (1 - np.sqrt(5 / RASTER.size)), abs=0.01)


def test_alleen_gemeenschappelijk_bereik_telt_mee():
    """Als het bibliotheekspectrum een deel niet gemeten heeft, telt een piek van het monster daar niet mee."""
    a = spectrum((700, 1.0, 10), (1700, 1.0, 15))
    half = RASTER > 1000
    b = a * half
    assert scores(a, b, "cosinus", masker_b=half) == pytest.approx(100.0, abs=0.01)
    assert scores(a, b, "cosinus", masker_b=VOL) < 90.0        # zonder masker zou de piek bij 700 "ontbreken"


def test_te_weinig_overlap_geeft_score_0():
    a = spectrum((700, 1.0, 10))
    klein = (RASTER > 600) & (RASTER < 900)                    # maar 75 punten
    assert scores(a, a * klein, "cosinus", masker_b=klein) == 0.0


def test_meerdere_vragen_tegelijk_geeft_zelfde_als_los():
    bib = mini_bibliotheek()
    samen = bereken_scores(bib.vectoren, bib.maskers, bib.vectoren_kwadraat, bib.vectoren[:3], bib.maskers[:3], "cosinus")
    assert samen.shape == (3, 5)
    for i in range(3):
        los = bereken_scores(bib.vectoren, bib.maskers, bib.vectoren_kwadraat, bib.vectoren[i], bib.maskers[i], "cosinus")
        assert np.allclose(samen[i], los[0], atol=1e-3)


def test_onbekende_methode_geeft_duidelijke_fout():
    with pytest.raises(ValueError, match="onbekende methode"):
        scores(np.ones(RASTER.size), np.ones(RASTER.size), "manhattan")


# --- De zoekfunctie ----------------------------------------------------------

@pytest.mark.parametrize("methode", METHODEN)
def test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer(methode):
    bib = mini_bibliotheek()
    monster = spectrum((1716, 1.0, 15), (1221, 0.58, 15), (2961, 0.32, 25))     # lijkt op stof A
    top = zoek(bib, monster, VOL, methode, top_n=5)
    assert top.iloc[0]["naam"] == "stof A"
    assert list(top["rang"]) == [1, 2, 3, 4]                # 4 stoffen, ook al zijn er 5 spectra
    assert top["nist_id"].is_unique
    assert top["score"].is_monotonic_decreasing
    assert 0 <= top["score"].min() and top["score"].max() <= 100
    assert {"naam", "cas", "formule", "fase", "score", "rij_index"} <= set(top.columns)


def test_negeer_identiek_laat_het_exacte_spectrum_weg():
    bib = mini_bibliotheek()
    gewoon = zoek(bib, bib.absorbantie[0], VOL, top_n=5)
    eerlijk = zoek(bib, bib.absorbantie[0], VOL, top_n=5, negeer_identiek=True)
    assert gewoon.iloc[0]["bestand"] == "A_IR_0.jdx" and gewoon.iloc[0]["score"] > 99.9
    assert eerlijk.iloc[0]["bestand"] == "A_IR_1.jdx"       # de ANDERE meting van stof A
    assert eerlijk.iloc[0]["score"] < 99.95


def test_waarschuwing_bij_lage_score_en_bij_klein_verschil():
    hoog_en_duidelijk = pd.DataFrame({"score": [95.0, 70.0]})
    laag = pd.DataFrame({"score": [40.0, 20.0]})
    dicht_bij_elkaar = pd.DataFrame({"score": [90.0, 89.5]})
    assert beoordeel_resultaat(hoog_en_duidelijk) == []
    assert any("laag" in w for w in beoordeel_resultaat(laag))
    assert any("dicht bij elkaar" in w for w in beoordeel_resultaat(dicht_bij_elkaar))
    assert len(beoordeel_resultaat(pd.DataFrame({"score": [50.0, 49.9]}))) == 2
    assert beoordeel_resultaat(pd.DataFrame()) != []


# --- Met de echte bibliotheek (overgeslagen als die ontbreekt) ---------------

def test_echte_bibliotheek_is_compleet(bibliotheek):
    assert len(bibliotheek) > 15_000
    assert bibliotheek.vectoren.shape == bibliotheek.absorbantie.shape == bibliotheek.maskers.shape
    assert bibliotheek.metadata["nist_id"].nunique() > 14_000
    assert (bibliotheek.metadata["duplicaat_van"] < 0).all()      # alleen unieke spectra geladen
    assert np.isfinite(bibliotheek.vectoren).all()


def test_aceton_wordt_herkend_ook_zonder_het_identieke_spectrum(bibliotheek, voorbeeldmap):
    v = bewerk_voor(lees_jcamp_bestand(voorbeeldmap / "aceton_gas_C67641_IR_0.jdx"))
    gewoon = zoek(bibliotheek, v.absorbantie, v.masker)
    assert gewoon.iloc[0]["cas"] == "67-64-1" and gewoon.iloc[0]["score"] > 99.9
    eerlijk = zoek(bibliotheek, v.absorbantie, v.masker, negeer_identiek=True)
    assert eerlijk.iloc[0]["cas"] == "67-64-1", f"top 5 was: {list(eerlijk['naam'])}"


@pytest.mark.parametrize("methode", METHODEN)
def test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde(bibliotheek, voorbeeldmap, methode):
    v = bewerk_voor(lees_jcamp_bestand(voorbeeldmap / "tolueen_vloeistof_C108883_IR_2.jdx"))
    zoek(bibliotheek, v.absorbantie, v.masker, methode)             # eerste keer: opwarmen
    start = time.perf_counter()
    top = zoek(bibliotheek, v.absorbantie, v.masker, methode)
    duur = time.perf_counter() - start
    print(f"\n[meting] zoeken ({methode}) door {len(bibliotheek)} spectra: {duur * 1000:.0f} ms")
    assert duur < 1.0
    assert top.iloc[0]["cas"] == "108-88-3"


# --- Klikken op pieken (de vertaling van een klik naar een piek) ---------------

def test_pieken_uit_selectie():
    from stofherkenner.grafieken import pieken_uit_selectie
    from stofherkenner.piekdetectie import Piek
    pieken = [Piek(1742.0, 1.0, 1.0, 50.0), Piek(1210.0, 0.5, 0.5, 40.0)]
    selectie = {"selection": {"points": [
        {"curve_number": 1, "x": 1742.0},      # klik op een rode stip
        {"curve_number": 0, "x": 1210.0},      # klik op de lijn: telt niet
        {"curve_number": 1, "x": 999.0},       # oude selectie van een ander bestand: bestaat niet meer
        {"curve_number": 1, "x": 1742.0},      # dubbel
    ]}}
    assert pieken_uit_selectie(selectie, pieken) == [1742.0]
    assert pieken_uit_selectie(None, pieken) == []
    assert pieken_uit_selectie({"selection": {"points": []}}, pieken) == []
    assert pieken_uit_selectie({"iets": "anders"}, pieken) == []
    assert pieken_uit_selectie({"selection": {"points": [{"curve_number": 1, "x": "onzin"}]}}, pieken) == []
