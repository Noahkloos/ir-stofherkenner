"""Tests voor de voorbewerking (eenheden, raster, normalisatie, vergelijkingsvorm)."""

from __future__ import annotations

import numpy as np
import pytest

from stofherkenner.jcamp_lezen import lees_jcamp_bestand, lees_jcamp_tekst
from stofherkenner.voorbewerking import (
    RASTER,
    VoorbewerkingFout,
    bewerk_voor,
    herken_x_eenheid,
    herken_y_eenheid,
    normaliseer,
    op_raster,
    vergelijkingsvorm,
    x_naar_golfgetal,
    y_naar_absorbantie,
)
from tests.conftest import gauss, maak_jcamp


def test_raster_is_550_tot_3798_in_stappen_van_4():
    assert RASTER[0] == 550 and RASTER[-1] == 3798 and len(RASTER) == 813
    assert np.allclose(np.diff(RASTER), 4.0)


@pytest.mark.parametrize("tekst,verwacht", [
    ("1/CM", "golfgetal"), ("cm-1", "golfgetal"), ("1/cm", "golfgetal"),
    ("MICROMETERS", "micrometer"), ("Microns", "micrometer"), ("NANOMETERS", "nanometer"), ("HZ", None),
])
def test_x_eenheid_herkennen(tekst, verwacht):
    assert herken_x_eenheid(tekst) == verwacht


@pytest.mark.parametrize("tekst,verwacht", [
    ("TRANSMITTANCE", "transmissie"), ("% Transmittance", "transmissie"), ("%T", "transmissie"),
    ("ABSORBANCE", "absorbantie"), ("(micromol/mol)-1m-1 (base 10)", "absorptiecoefficient"),
    ("Reflectance", None), ("dispersion index", None),
])
def test_y_eenheid_herkennen(tekst, verwacht):
    assert herken_y_eenheid(tekst) == verwacht


def test_micrometer_naar_golfgetal():
    # 10 000 / micrometer: 2,5 um = 4000 cm-1; 5,8 um = 1724 cm-1; 10 um = 1000 cm-1
    assert np.allclose(x_naar_golfgetal(np.array([2.5, 5.8, 10.0]), "micrometer"), [4000.0, 1724.14, 1000.0], atol=0.01)
    assert np.allclose(x_naar_golfgetal(np.array([2500.0]), "nanometer"), [4000.0])
    with pytest.raises(VoorbewerkingFout):
        x_naar_golfgetal(np.array([0.0, 5.0]), "micrometer")


def test_transmissie_naar_absorbantie():
    # A = -log10(T): T=1 -> 0; T=0,1 -> 1; T=0,01 -> 2
    assert np.allclose(y_naar_absorbantie(np.array([1.0, 0.1, 0.01]), "transmissie"), [0.0, 1.0, 2.0])
    # procenten worden herkend (waarden boven 2 of een %-teken in de eenheid)
    assert np.allclose(y_naar_absorbantie(np.array([100.0, 10.0, 50.0]), "transmissie"), [0.0, 1.0, 0.30103], atol=1e-5)
    assert np.allclose(y_naar_absorbantie(np.array([1.0, 0.5]), "transmissie", "% TRANSMITTANCE"), [2.0, 2.0])   # 1% en 0,5% -> ondergrens
    # ondergrens voorkomt log(0): T=0 geeft A=2 in plaats van oneindig
    assert np.allclose(y_naar_absorbantie(np.array([0.0, -0.05]), "transmissie"), [2.0, 2.0])
    # absorbantie blijft zoals hij is
    assert np.allclose(y_naar_absorbantie(np.array([0.3, 1.2]), "absorbantie"), [0.3, 1.2])


def test_piek_blijft_op_zijn_plek_na_omzetten_naar_raster():
    x = np.arange(400.0, 4000.0, 1.0)
    waarden, masker = op_raster(x, gauss(x, 1714.0, 1.0, 10.0))
    assert masker.all()
    assert abs(RASTER[np.argmax(waarden)] - 1714.0) <= 2.0


def test_masker_geeft_gemeten_bereik_aan():
    x = np.arange(700.0, 3000.0, 2.0)
    waarden, masker = op_raster(x, np.ones_like(x))
    assert not masker[RASTER < 700].any() and not masker[RASTER > 2998].any()
    assert masker[(RASTER >= 700) & (RASTER <= 2998)].all()
    assert np.all(waarden[~masker] == 0)


def test_hoge_en_lage_resolutie_geven_bijna_hetzelfde_raster():
    """Dezelfde meting met 0,25 cm-1 en met 4 cm-1 stap moet op het raster (bijna) gelijk zijn."""
    def spectrum(stap):
        x = np.arange(500.0, 3900.0, stap)
        return x, gauss(x, 1200, 0.6, 15) + gauss(x, 1740, 1.0, 12) + gauss(x, 2960, 0.4, 25)
    fijn, _ = op_raster(*spectrum(0.25))
    grof, _ = op_raster(*spectrum(4.0))
    cosinus = fijn @ grof / (np.linalg.norm(fijn) * np.linalg.norm(grof))
    assert cosinus > 0.999


def test_normaliseren_zet_basislijn_op_0_en_maximum_op_1():
    masker = np.ones(RASTER.size, dtype=bool)
    a = normaliseer(0.2 + 3.0 * gauss(RASTER, 1700, 1, 20), masker)
    assert a.min() == pytest.approx(0.0, abs=1e-9) and a.max() == pytest.approx(1.0)
    with pytest.raises(VoorbewerkingFout):
        normaliseer(np.full(RASTER.size, 0.5), masker)            # volledig vlak spectrum


def test_micrometer_en_golfgetal_van_aceton_komen_overeen(voorbeeldmap):
    """Twee bestanden van aceton (1/CM + absorbantie, en micrometer + transmissie) leveren dezelfde C=O-piek op."""
    a = bewerk_voor(lees_jcamp_bestand(voorbeeldmap / "aceton_gas_C67641_IR_0.jdx"))
    b = bewerk_voor(lees_jcamp_bestand(voorbeeldmap / "aceton_gas_micrometer_C67641_IR_1.jdx"))
    assert (a.x_soort, a.y_soort) == ("golfgetal", "absorbantie")
    assert (b.x_soort, b.y_soort) == ("micrometer", "transmissie")
    gebied = (RASTER > 1650) & (RASTER < 1800)
    piek_a = RASTER[gebied][np.argmax(a.absorbantie[gebied])]
    piek_b = RASTER[gebied][np.argmax(b.absorbantie[gebied])]
    assert 1700 <= piek_a <= 1760 and 1700 <= piek_b <= 1760
    assert abs(piek_a - piek_b) <= 16


def test_te_smal_spectrum_wordt_geweigerd():
    x = np.arange(1000.0, 1500.0, 2.0)
    with pytest.raises(VoorbewerkingFout, match="bedekt maar"):
        bewerk_voor(lees_jcamp_tekst(maak_jcamp(x, gauss(x, 1200, 1, 10))))


def test_vergelijkingsvorm_negeert_basislijn_en_schaal():
    """Een constante basislijnverschuiving en een andere schaal veranderen de vergelijkingsvorm (bijna) niet."""
    masker = np.ones(RASTER.size, dtype=bool)
    basis = normaliseer(gauss(RASTER, 1100, 0.5, 20) + gauss(RASTER, 1700, 1.0, 15), masker)
    vorm = vergelijkingsvorm(basis, masker)
    assert vorm.shape == RASTER.shape and np.abs(vorm).max() == pytest.approx(1.0)
    # matrix-invoer geeft per rij hetzelfde als losse invoer
    matrix = vergelijkingsvorm(np.vstack([basis, basis]), np.vstack([masker, masker]))
    assert np.allclose(matrix[0], vorm) and np.allclose(matrix[1], vorm)
    # buiten het masker is de vergelijkingsvorm altijd 0
    half = masker.copy()
    half[:200] = False
    assert np.all(vergelijkingsvorm(basis * half, half)[:200] == 0)
