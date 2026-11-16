"""Tests voor de JCAMP-DX-parser."""

from __future__ import annotations

import numpy as np
import pytest

from stofherkenner.jcamp_lezen import JcampFout, lees_jcamp_bestand, lees_jcamp_tekst
from tests.conftest import gauss, maak_jcamp


def test_kop_en_data_van_aceton(voorbeeldmap):
    s = lees_jcamp_bestand(voorbeeldmap / "aceton_gas_C67641_IR_0.jdx")
    assert s.titel == "Acetone"
    assert s.cas == "67-64-1"
    assert s.formule == "C 3 H 6 O"
    assert s.x_eenheid == "1/CM" and s.y_eenheid == "ABSORBANCE"
    assert s.toestand == "gas"
    assert s.x.size == s.npoints_label == 880
    # FIRSTX=450, LASTX=3966, DELTAX=4 volgens de kop van het bestand
    assert s.x[0] == pytest.approx(450.0) and s.x[-1] == pytest.approx(3966.0)
    assert np.allclose(np.diff(s.x), 4.0)
    # eerste y = 40 x YFACTOR (0.000078659) = FIRSTY (0.003146)
    assert s.y[0] == pytest.approx(0.003146, abs=1e-6)
    assert s.y.max() == pytest.approx(0.78659, abs=1e-5)      # MAXY uit de kop


def test_micrometer_bestand_houdt_eigen_eenheid(voorbeeldmap):
    s = lees_jcamp_bestand(voorbeeldmap / "aceton_gas_micrometer_C67641_IR_1.jdx")
    assert s.x_eenheid == "MICROMETERS" and s.y_eenheid == "TRANSMITTANCE"
    assert 2.0 < s.x.min() < 3.0 and 14.0 < s.x.max() < 17.0     # golflengte in micrometer
    assert s.x.size == s.npoints_label


def test_xfactor_en_yfactor_worden_toegepast():
    tekst = ("##TITLE=t\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n##XFACTOR=2.0\n##YFACTOR=0.001\n"
             "##FIRSTX=1000\n##LASTX=1008\n##NPOINTS=5\n##XYDATA=(X++(Y..Y))\n500 100 200 300\n503 400 500\n##END=\n")
    s = lees_jcamp_tekst(tekst)
    assert np.allclose(s.x, [1000, 1002, 1004, 1006, 1008])
    assert np.allclose(s.y, [0.1, 0.2, 0.3, 0.4, 0.5])


def test_aflopende_x_as():
    x = np.arange(4000.0, 499.0, -4.0)
    s = lees_jcamp_tekst(maak_jcamp(x, gauss(x, 1700, 1, 10)))
    assert s.x[0] == pytest.approx(4000.0) and s.x[-1] == pytest.approx(500.0)
    assert s.x[np.argmax(s.y)] == pytest.approx(1700.0)


def test_aan_elkaar_geplakte_getallen_met_mintekens():
    """In JCAMP mag een minteken ook als scheidingsteken dienen: '10-20-30'."""
    tekst = ("##TITLE=t\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n"
             "##FIRSTX=100\n##LASTX=103\n##NPOINTS=4\n##XYDATA=(X++(Y..Y))\n100+10-20+30-40\n##END=\n")
    assert np.allclose(lees_jcamp_tekst(tekst).y, [10, -20, 30, -40])


def test_gecomprimeerde_data_difdup():
    """ASDF-compressie (SQZ + DIF + DUP), zoals sommige spectrometers exporteren.

    Regel 1: x=100; A0 = +10 (SQZ); J = +1 -> 11 (DIF); T = herhaal het verschil 2 extra keer -> 12, 13
             (de laatste waarde, 13, is tegelijk de controlewaarde voor de volgende regel)
    Regel 2: x=103; A3 = 13 (controle, vervalt); j = -1 -> 12; K = +2 -> 14
    Verwacht: 10, 11, 12, 13, 12, 14
    """
    tekst = ("##TITLE=t\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n"
             "##FIRSTX=100\n##LASTX=105\n##NPOINTS=6\n##XYDATA=(X++(Y..Y))\n100A0JT\n103A3jK\n##END=\n")
    s = lees_jcamp_tekst(tekst)
    assert np.allclose(s.y, [10, 11, 12, 13, 12, 14])
    assert np.allclose(s.x, [100, 101, 102, 103, 104, 105])


def test_xypoints_en_peak_table():
    for label in ("XYPOINTS=(XY..XY)", "PEAK TABLE=(XY..XY)"):
        tekst = (f"##TITLE=t\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n##NPOINTS=3\n"
                 f"##{label}\n1000.0, 0.5; 1700.0, 1.0\n2950.0, 0.3\n##END=\n")
        s = lees_jcamp_tekst(tekst)
        assert np.allclose(s.x, [1000, 1700, 2950]) and np.allclose(s.y, [0.5, 1.0, 0.3])
        assert s.datablok_soort == label.split("=")[0]


def test_meerdere_blokken_neemt_eerste_met_data():
    x = np.arange(500.0, 1000.0, 4.0)
    leeg = "##TITLE=leeg blok\n##JCAMP-DX=4.24\n##NPOINTS=0\n##END=\n"
    tekst = leeg + maak_jcamp(x, gauss(x, 700, 1, 10), titel="tweede blok")
    s = lees_jcamp_tekst(tekst)
    assert s.titel == "tweede blok" and s.aantal_blokken == 2 and s.x.size == len(x)


def test_bestand_zonder_data_geeft_jcampfout():
    with pytest.raises(JcampFout):
        lees_jcamp_tekst("##TITLE=alleen kop\n##JCAMP-DX=4.24\n##NPOINTS=0\n##END=\n")


def test_opmerkingen_met_dollartekens_worden_genegeerd():
    tekst = ("##TITLE=t $$ opmerking\n##JCAMP-DX=4.24 $$ By DXEDIT\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n"
             "##FIRSTX=1\n##LASTX=3\n##NPOINTS=3\n##XYDATA=(X++(Y..Y))\n$$ commentaarregel\n1 5 6 7\n##END=\n")
    s = lees_jcamp_tekst(tekst)
    assert s.titel == "t" and np.allclose(s.y, [5, 6, 7])


def test_zelfde_uitkomst_als_bibliotheek_jcamp(voorbeeldmap):
    """Onafhankelijke controle: onze parser geeft dezelfde punten als de bibliotheek 'jcamp'."""
    jcamp = pytest.importorskip("jcamp", reason="pakket 'jcamp' is alleen nodig voor het onderzoek (research/requirements.txt)")
    lees = getattr(jcamp, "jcamp_readfile", None) or jcamp.readfile       # de naam verschilt per versie
    for pad in sorted(voorbeeldmap.glob("*.jdx")):
        eigen = lees_jcamp_bestand(pad)
        ander = lees(str(pad))
        assert len(ander["x"]) == eigen.x.size, pad.name
        assert np.allclose(ander["x"], eigen.x, rtol=1e-4, atol=1e-3), pad.name
        assert np.allclose(ander["y"], eigen.y, rtol=1e-4, atol=1e-6), pad.name
