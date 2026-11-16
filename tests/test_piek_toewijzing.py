"""Tests voor de toewijzing van pieken (de tabel die je ziet als je op een rode piekmarkering klikt)."""

from __future__ import annotations

import pytest

from stofherkenner.analyse import analyseer, lees_en_valideer
from stofherkenner.piek_toewijzing import (
    CORRELATIETABEL,
    intensiteitsklasse,
    mogelijke_bindingen,
    piekentabel,
    regels_per_piek,
)
from stofherkenner.piekdetectie import Piek


def piek(golfgetal: float, breedte: float = 20.0, hoogte: float = 0.5) -> Piek:
    return Piek(golfgetal=golfgetal, hoogte=hoogte, prominentie=hoogte, breedte=breedte)


def eerste(golfgetal: float, breedte: float = 20.0, hoogte: float = 0.5) -> str:
    return mogelijke_bindingen(piek(golfgetal, breedte, hoogte))[0]


def test_correlatietabel_is_consistent():
    for g in CORRELATIETABEL:
        assert 400 <= g.laag < g.hoog <= 4000, g
        assert g.trilling and g.groep
        assert g.tekst == f"{g.trilling} – {g.groep}"


@pytest.mark.parametrize("golfgetal,breedte,hoogte,verwacht", [
    (1715, 20, 0.9, "ν(C=O) – keton of aldehyde"),
    (2230, 15, 0.4, "ν(C≡N) – nitril"),
    (2925, 30, 0.9, "ν(C–H) – alkylgroep"),
    (3002, 40, 0.1, "ν(C–H) – alkylgroep"),           # CH3 naast C=O (aceton), géén =C–H
    (3080, 25, 0.2, "ν(=C–H) – alkeen of aromaat"),
    (3650, 40, 0.2, "ν(O–H), vrij"),                    # vrije O–H (gasfase)
    (3350, 250, 0.8, "ν(O–H), waterstofbrug"),          # brede O–H-band (vloeistof)
    (1642, 30, 0.1, "ν(C=C) – alkeen"),                 # alkeen vóór amide
    (2349, 20, 0.3, "ν(O=C=O) – CO₂ uit de lucht"),     # meetartefact
    (1502, 19, 0.39, "ν(C=C) – aromatische ring"),      # tolueen: ring vóór NO2
    (1610, 16, 0.19, "ν(C=C) – aromatische ring"),      # aromaat vóór N–H-buiging
    (646, 129, 0.13, "γ(O–H) – alcohol"),               # ethanol (vloeistof): brede O–H, niet C–Cl
])
def test_bekende_banden(golfgetal, breedte, hoogte, verwacht):
    assert eerste(golfgetal, breedte, hoogte).startswith(verwacht)


def test_breedte_bepaalt_oh_of_nh():
    smal = mogelijke_bindingen(piek(3350, breedte=40))
    breed = mogelijke_bindingen(piek(3350, breedte=250))
    assert not any("waterstofbrug" in m for m in smal) and any(m.startswith("ν(N–H)") for m in smal)
    assert any("waterstofbrug" in m for m in breed)


def test_boventonen_alleen_bij_zwakke_pieken():
    assert any("boventonen" in m for m in mogelijke_bindingen(piek(1950, hoogte=0.05)))
    assert not any("boventonen" in m for m in mogelijke_bindingen(piek(1766, hoogte=0.63)))


def test_c_o_strek_van_zuur_staat_bij_de_mogelijkheden():
    """De carbonzuurregel noemt een C–O-rek tot 1320 cm⁻¹; de tabel moet die mogelijkheid ook geven."""
    assert any(m.startswith("ν(C–O) –") for m in mogelijke_bindingen(piek(1286, 21, 0.66)))


@pytest.mark.parametrize("hoogte,klasse", [(0.95, "sterk"), (0.5, "sterk"), (0.3, "middel"), (0.15, "middel"), (0.05, "zwak")])
def test_intensiteitsklasse(hoogte, klasse):
    assert intensiteitsklasse(hoogte) == klasse


def test_rij_bevat_intensiteit_bandvorm_en_vingerafdruk():
    rijen = piekentabel([piek(1100, breedte=150, hoogte=0.6), piek(1715, breedte=20, hoogte=0.05)], [])
    hoog, laag = rijen                                           # van hoog naar laag golfgetal
    assert (hoog.golfgetal, hoog.intensiteit, hoog.bandvorm, hoog.vingerafdruk) == (1715, "zwak", "scherp", False)
    assert (laag.golfgetal, laag.intensiteit, laag.bandvorm, laag.vingerafdruk) == (1100, "sterk", "breed", True)
    assert laag.als_dict()["Intensiteit"] == "sterk (0.60)"


def test_piek_buiten_alle_gebieden():
    rij = piekentabel([piek(2450)], [])[0]
    assert rij.toewijzingen == []
    assert rij.als_dict()["Mogelijke toewijzingen"] == "geen standaardtoewijzing"


def test_tabel_gesorteerd_van_hoog_naar_laag_golfgetal():
    rijen = piekentabel([piek(1100), piek(3000), piek(1715)], [])
    assert [r.golfgetal for r in rijen] == [3000, 1715, 1100]


def test_regels_worden_aan_de_juiste_piek_gekoppeld(voorbeeldmap):
    """De tabel spreekt het paneel met functionele groepen niet tegen: ethylacetaat 1766 cm⁻¹ = ester volgens de regels."""
    pad = voorbeeldmap / "ethylacetaat_gas_C141786_IR_0.jdx"
    a = analyseer(lees_en_valideer(pad.name, pad.read_bytes()), None)
    per_piek = regels_per_piek(a.bevindingen)
    ester_1766 = [t for t in per_piek[1766] if t.groep == "Ester (–COO–)"]
    assert ester_1766 and ester_1766[0].kenmerk == "C=O-rek (ester)" and ester_1766[0].zekerheid == "hoog"
    assert any(t.groep == "Ester (–COO–)" and t.kenmerk.startswith("C–O–C-rek") for t in per_piek[1242])
    rij = next(r for r in piekentabel(a.pieken, a.bevindingen) if r.golfgetal == 1766)
    assert any(t.groep == "Ester (–COO–)" for t in rij.regels)
    assert any("ester" in t for t in rij.toewijzingen)


def test_elke_door_een_regel_genoemde_piek_staat_in_de_tabel(voorbeeldmap):
    """Voor alle tien voorbeeldbestanden: elke piek die een regel noemt, krijgt in de tabel die regel erbij."""
    for pad in sorted(voorbeeldmap.glob("*.jdx")):
        a = analyseer(lees_en_valideer(pad.name, pad.read_bytes()), None)
        rijen = {r.golfgetal: r for r in piekentabel(a.pieken, a.bevindingen)}
        for golfgetal, regels in regels_per_piek(a.bevindingen).items():
            assert golfgetal in rijen, f"{pad.name}: piek {golfgetal} uit de regels ontbreekt in de tabel"
            for regel in regels:
                assert regel in rijen[golfgetal].regels, pad.name
