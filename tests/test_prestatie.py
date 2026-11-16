"""Snelheidstest (US, kwaliteitscriterium 1).

Eis: uploaden en parsen van een JCAMP-DX-bestand tot 5 MB duurt maximaal
2 seconden tot de grafiek zichtbaar is.

Wat we hier meten is alles wat de server doet tussen "bestand ontvangen" en
"grafiek klaar om te tonen": valideren, inlezen, voorbewerken, pieken zoeken,
functionele groepen bepalen en de Plotly-grafiek opbouwen. (Het zoeken in de
bibliotheek wordt apart gemeten in test_matching.py en de evaluatie.)
De gemeten tijd wordt afgedrukt en staat in docs/testresultaten.md.
"""

from __future__ import annotations

import time

import numpy as np

from stofherkenner.analyse import analyseer, lees_en_valideer
from stofherkenner.grafieken import MAX_PUNTEN_IN_GRAFIEK, dun_uit, spectrum_grafiek
from stofherkenner.validatie import MAX_BESTANDSGROOTTE
from tests.conftest import gauss, maak_jcamp

MAX_SECONDEN = 2.0


def maak_bestand_van_ongeveer_5_mb() -> bytes:
    """Genereer een geldig JCAMP-DX-bestand van net onder de 5 MB (ruim 560 000 meetpunten)."""
    aantal = 565_000
    x = np.linspace(400.0, 4000.0, aantal)
    rng = np.random.default_rng(0)
    y = (gauss(x, 1715, 1.0, 12) + gauss(x, 1220, 0.6, 15) + gauss(x, 2960, 0.3, 25)
         + 0.02 + rng.normal(0, 0.002, aantal))
    return maak_jcamp(x, y, titel="Gegenereerd testbestand van ongeveer 5 MB").encode("utf-8")


def verwerk_tot_grafiek(inhoud: bytes):
    """Precies de stappen die de app doet voordat de grafiek zichtbaar is."""
    analyse = lees_en_valideer("groot.jdx", inhoud)
    analyse = analyseer(analyse, bibliotheek=None)
    figuur = spectrum_grafiek(analyse.golfgetal, analyse.spectrum.y, "Absorbantie", analyse.pieken)
    figuur.to_json()                      # dit is wat naar de browser gestuurd wordt
    return analyse, figuur


def test_bestand_van_5_mb_binnen_2_seconden():
    inhoud = maak_bestand_van_ongeveer_5_mb()
    grootte_mb = len(inhoud) / 1024 / 1024
    assert 4.7 < grootte_mb <= 5.0, f"testbestand is {grootte_mb:.2f} MB"
    assert len(inhoud) <= MAX_BESTANDSGROOTTE

    tijden = []
    for _ in range(3):                    # drie keer meten; de langzaamste telt
        start = time.perf_counter()
        analyse, figuur = verwerk_tot_grafiek(inhoud)
        tijden.append(time.perf_counter() - start)

    print(f"\n[meting] bestand van {grootte_mb:.2f} MB, {analyse.spectrum.x.size} meetpunten: "
          f"valideren + inlezen + analyseren + grafiek in {min(tijden):.2f} s (snelste) / {max(tijden):.2f} s (langzaamste van 3)")
    assert max(tijden) < MAX_SECONDEN
    assert analyse.spectrum.x.size == 565_000
    # de drie ingebouwde pieken zijn gevonden
    posities = [p.golfgetal for p in analyse.pieken]
    for verwacht in (1220, 1715, 2960):
        assert any(abs(p - verwacht) <= 8 for p in posities), posities


def test_grafiek_wordt_uitgedund_maar_houdt_de_pieken():
    """De grafiek bevat hooguit een paar duizend punten (snel in de browser), maar de piektop blijft behouden."""
    x = np.linspace(400.0, 4000.0, 500_000)
    y = gauss(x, 1715, 1.0, 3)
    x_dun, y_dun = dun_uit(x, y)
    assert len(x_dun) <= MAX_PUNTEN_IN_GRAFIEK
    assert y_dun.max() > 0.999
    assert np.all(np.diff(x_dun) >= 0)


def test_te_groot_bestand_wordt_snel_afgewezen():
    """Een bestand boven 5 MB wordt afgekeurd zonder dat het eerst helemaal ingelezen wordt."""
    import pytest

    from stofherkenner.validatie import ValidatieFout
    inhoud = maak_bestand_van_ongeveer_5_mb() + b"\n" * 400_000
    assert len(inhoud) > MAX_BESTANDSGROOTTE
    start = time.perf_counter()
    with pytest.raises(ValidatieFout):
        lees_en_valideer("groot.jdx", inhoud)
    assert time.perf_counter() - start < 0.1
