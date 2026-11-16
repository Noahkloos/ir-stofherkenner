"""Tests voor de structuurformules (ophalen, controleren, bewaren, tekenen).

Deze tests gaan nooit naar internet: het downloaden wordt vervangen door een
nepfunctie die een zelfgeschreven molfile of een foutpagina teruggeeft.
"""

from __future__ import annotations

import pytest

from stofherkenner import structuren as s

# Zelfgeschreven 2D-molfile van aceton (CH3-CO-CH3): 4 atomen, 3 bindingen.
ACETON_MOL = """aceton (zelfgeschreven testbestand)
  test

  4  3  0  0  0  0  0  0  0  0999 V2000
    0.8660    0.5000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.7320    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.8660    1.5000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
  1  4  2  0
M  END
"""
LEEG_MOL = """onbekend
  test

  0  0  0  0  0  0  0  0  0  0999 V2000
M  END
"""


@pytest.fixture()
def online_nep(monkeypatch):
    """Doe alsof er internet is, met een nepdownload. Geeft een lijst met de opgevraagde ID's terug."""
    gevraagd: list[str] = []
    antwoorden: dict[str, str | None] = {}

    def nep_download(nist_id: str):
        gevraagd.append(nist_id)
        return antwoorden.get(nist_id)

    monkeypatch.setattr(s, "OFFLINE", False)
    monkeypatch.setattr(s, "_download", nep_download)
    monkeypatch.setattr(s, "_mislukt", {})
    return gevraagd, antwoorden


@pytest.mark.parametrize("nist_id,geldig", [
    ("C67641", True), ("B6000033", True), ("C999999999", True),
    ("../geheim", False), ("C67641.mol", False), ("67-64-1", False), ("", False), ("X12345", False),
])
def test_alleen_echte_nist_ids(nist_id, geldig):
    assert s.is_geldig_id(nist_id) == geldig


def test_aantal_atomen():
    assert s.aantal_atomen(ACETON_MOL) == 4
    assert s.aantal_atomen(LEEG_MOL) == 0
    assert s.aantal_atomen("<html>Fout 500</html>") == -1


def test_tekenen_geeft_svg():
    svg = s.teken_svg(ACETON_MOL)
    assert svg is not None and svg.startswith("<svg") and "</svg>" in svg
    assert s.teken_svg("dit is geen molfile") is None
    assert s.teken_svg("") is None


def test_ophalen_en_bewaren(tmp_path, online_nep):
    gevraagd, antwoorden = online_nep
    antwoorden["C67641"] = ACETON_MOL
    assert s.haal_molfile("C67641", tmp_path) == ACETON_MOL
    assert (tmp_path / "C67641.mol").exists()
    assert s.haal_molfile("C67641", tmp_path) == ACETON_MOL       # tweede keer uit de cache
    assert gevraagd == ["C67641"]                                   # dus maar één keer gedownload


def test_windows_regeleindes_overleven_de_cache(tmp_path, online_nep):
    """NIST levert '\\r\\n'. Na opslaan en weer inlezen moet de structuur nog steeds te tekenen zijn
    (fout gevonden in de browser: tweede keer, uit de cache, mislukte het tekenen)."""
    gevraagd, antwoorden = online_nep
    antwoorden["C67641"] = ACETON_MOL.replace("\n", "\r\n")
    assert s.structuur_svg("C67641", tmp_path) is not None           # eerste keer: van "internet"
    assert b"\r" not in (tmp_path / "C67641.mol").read_bytes()
    assert s.structuur_svg("C67641", tmp_path) is not None           # tweede keer: uit de cache
    assert gevraagd == ["C67641"]


def test_al_beschadigde_cachebestanden_worden_hersteld(tmp_path):
    (tmp_path / "C67641.mol").write_bytes(ACETON_MOL.replace("\n", "\r\r\n").encode("latin-1"))
    assert s.structuur_svg("C67641", tmp_path, online=False) is not None


def test_foutpagina_wordt_niet_bewaard(tmp_path, online_nep):
    gevraagd, antwoorden = online_nep
    antwoorden["C2000"] = "<html>Service unavailable</html>"      # NIST geeft een foutpagina
    assert s.haal_molfile("C2000", tmp_path) is None
    assert not (tmp_path / "C2000.mol").exists()
    # kort daarna niet opnieuw proberen (geen vertraging bij elke klik in de app)
    assert s.haal_molfile("C2000", tmp_path) is None
    assert gevraagd.count("C2000") == 1


def test_geen_structuur_bij_nist_wordt_onthouden(tmp_path, online_nep):
    gevraagd, antwoorden = online_nep
    antwoorden["C999999999"] = LEEG_MOL                             # zo antwoordt NIST bij een onbekende stof
    assert s.haal_molfile("C999999999", tmp_path) is None
    assert (tmp_path / "C999999999.mol").read_text(encoding="latin-1") == s.GEEN_STRUCTUUR
    assert s.haal_molfile("C999999999", tmp_path) is None
    assert gevraagd == ["C999999999"]


def test_netwerkfout_wordt_niet_bewaard(tmp_path, online_nep):
    gevraagd, _ = online_nep                                       # geen antwoord = netwerkfout (None)
    assert s.haal_molfile("C3000", tmp_path) is None
    assert not (tmp_path / "C3000.mol").exists()


def test_offline_of_uitgeschakeld_gaat_niet_naar_internet(tmp_path, online_nep):
    gevraagd, antwoorden = online_nep
    antwoorden["C67641"] = ACETON_MOL
    assert s.haal_molfile("C67641", tmp_path, online=False) is None   # schakelaar in de app staat uit
    assert gevraagd == []


def test_ongeldig_id_gaat_nooit_naar_internet(tmp_path, online_nep):
    gevraagd, _ = online_nep
    assert s.haal_molfile("../../etc/passwd", tmp_path) is None
    assert gevraagd == []


def test_tests_draaien_offline():
    """conftest.py zet de omgevingsvariabele; de module heeft hem bij het laden gelezen."""
    assert s.OFFLINE is True
