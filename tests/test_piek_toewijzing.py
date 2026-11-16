"""Tests voor de toewijzing van pieken aan bindingen (de tabel die je ziet als je op een rode stip klikt)."""

from __future__ import annotations

import pytest

from stofherkenner.analyse import analyseer, lees_en_valideer
from stofherkenner.piek_toewijzing import CORRELATIETABEL, mogelijke_bindingen, piekentabel, regels_per_piek
from stofherkenner.piekdetectie import Piek


def piek(golfgetal: float, breedte: float = 20.0, hoogte: float = 0.5) -> Piek:
    return Piek(golfgetal=golfgetal, hoogte=hoogte, prominentie=hoogte, breedte=breedte)


def eerste_binding(golfgetal: float, breedte: float = 20.0) -> str:
    return mogelijke_bindingen(piek(golfgetal, breedte))[0]


def test_correlatietabel_is_consistent():
    for g in CORRELATIETABEL:
        assert 400 <= g.laag < g.hoog <= 4000, g
        assert g.binding and g.omschrijving


@pytest.mark.parametrize("golfgetal,breedte,verwacht", [
    (1715, 20, "C=O: rek, keton"),          # C=O van een keton
    (2230, 15, "C≡N"),                      # nitril
    (2925, 30, "C–H: rek, alkaan"),         # alkaan C–H
    (3002, 40, "C–H: rek, alkaan"),         # CH3 naast C=O (aceton), géén =C–H
    (3080, 25, "=C–H"),                     # alkeen/aromaat C–H boven 3000
    (3650, 40, "O–H: vrije rek"),           # vrije O–H (gasfase)
    (3350, 250, "O–H: rek met waterstofbruggen"),   # brede O–H-band (vloeistof)
    (1642, 30, "C=C: rek, alkeen"),         # alkeen C=C vóór amide
    (2349, 20, "O=C=O"),                    # CO2 uit de lucht
])
def test_bekende_banden(golfgetal, breedte, verwacht):
    assert eerste_binding(golfgetal, breedte).startswith(verwacht)


def test_breedte_bepaalt_oh_of_nh():
    smal = mogelijke_bindingen(piek(3350, breedte=40))
    breed = mogelijke_bindingen(piek(3350, breedte=250))
    assert not any("waterstofbruggen" in m for m in smal) and any(m.startswith("N–H") for m in smal)
    assert any("waterstofbruggen" in m for m in breed)


def test_piek_buiten_alle_gebieden_geeft_eerlijk_antwoord():
    rijen = piekentabel([piek(2450)], [])
    assert "geen standaardtoewijzing" in rijen[0]["Mogelijke binding(en)"]


def test_vingerafdrukgebied_wordt_vermeld():
    rijen = piekentabel([piek(1100), piek(1715)], [])
    per_golfgetal = {r["Golfgetal (cm⁻¹)"]: r["Mogelijke binding(en)"] for r in rijen}
    assert "vingerafdrukgebied" in per_golfgetal[1100]
    assert "vingerafdrukgebied" not in per_golfgetal[1715]


def test_tabel_gesorteerd_van_hoog_naar_laag_golfgetal():
    rijen = piekentabel([piek(1100), piek(3000), piek(1715)], [])
    assert [r["Golfgetal (cm⁻¹)"] for r in rijen] == [3000, 1715, 1100]


def test_regels_worden_aan_de_juiste_piek_gekoppeld(voorbeeldmap):
    """De tabel spreekt het paneel met functionele groepen niet tegen: ethylacetaat 1766 cm⁻¹ = ester volgens de regels."""
    pad = voorbeeldmap / "ethylacetaat_gas_C141786_IR_0.jdx"
    a = analyseer(lees_en_valideer(pad.name, pad.read_bytes()), None)
    per_piek = regels_per_piek(a.bevindingen)
    assert any(t.startswith("Ester (–COO–): C=O-rek (ester)") for t in per_piek[1766])
    assert any(t.startswith("Ester (–COO–): C–O–C-rek") for t in per_piek[1242])
    rijen = {r["Golfgetal (cm⁻¹)"]: r for r in piekentabel(a.pieken, a.bevindingen)}
    assert "Ester" in rijen[1766]["Volgens de regels"]
    assert "ester" in rijen[1766]["Mogelijke binding(en)"]


def test_elke_door_een_regel_genoemde_piek_staat_in_de_tabel(voorbeeldmap):
    """Voor alle tien voorbeeldbestanden: elke piek die een regel noemt, krijgt in de tabel die regel erbij."""
    for pad in sorted(voorbeeldmap.glob("*.jdx")):
        a = analyseer(lees_en_valideer(pad.name, pad.read_bytes()), None)
        rijen = {r["Golfgetal (cm⁻¹)"]: r for r in piekentabel(a.pieken, a.bevindingen)}
        for golfgetal, regels in regels_per_piek(a.bevindingen).items():
            assert golfgetal in rijen, f"{pad.name}: piek {golfgetal} uit de regels ontbreekt in de tabel"
            for regel in regels:
                assert regel in rijen[golfgetal]["Volgens de regels"], pad.name


def test_boventonen_alleen_bij_zwakke_pieken():
    zwak = mogelijke_bindingen(piek(1950, hoogte=0.05))
    sterk = mogelijke_bindingen(piek(1766, hoogte=0.63))
    assert any("boventonen" in m for m in zwak)
    assert not any("boventonen" in m for m in sterk)


@pytest.mark.parametrize("golfgetal,breedte,hoogte,verwacht_eerst", [
    (1502, 19, 0.39, "C=C: ringtrilling, aromaat"),     # tolueen: ring vóór NO2
    (1286, 21, 0.66, "C–O–C"),                            # azijnzuur: C–O-gebied omvat 1286 ...
    (646, 129, 0.13, "O–H: brede buiging"),               # ethanol (oplossing): brede O–H-wag, niet C–Cl
])
def test_bekende_lastige_pieken(golfgetal, breedte, hoogte, verwacht_eerst):
    mogelijk = mogelijke_bindingen(piek(golfgetal, breedte, hoogte))
    assert mogelijk[0].startswith(verwacht_eerst), mogelijk


def test_c_o_rek_van_zuur_staat_bij_de_mogelijkheden():
    """De carbonzuurregel noemt een C–O-rek tot 1320 cm⁻¹; de tabel moet die mogelijkheid ook geven."""
    assert any(m.startswith("C–O: rek") for m in mogelijke_bindingen(piek(1286, 21, 0.66)))
