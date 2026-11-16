"""Tests voor het automatisch opzetten van de bibliotheek (Streamlit Cloud) en het bouwen uit een zip."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest

from stofherkenner.opzet import moet_automatisch_bouwen
from tests.conftest import PROJECTMAP


def laad_build_library():
    spec = importlib.util.spec_from_file_location("build_library", PROJECTMAP / "scripts" / "build_library.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("instelling,pad,verwacht", [
    ("1", Path("C:/claude code/ir-stofherkenner"), True),       # handmatig aangezet
    ("0", Path("/mount/src/ir-stofherkenner"), False),          # handmatig uitgezet (zoals in de tests)
    ("", Path("/mount/src/ir-stofherkenner"), True),            # Streamlit Cloud
    ("", Path("C:/claude code/ir-stofherkenner"), False),       # eigen laptop: daar is setup.bat voor
])
def test_wanneer_automatisch_bouwen(monkeypatch, instelling, pad, verwacht):
    monkeypatch.setenv("IR_STOFHERKENNER_AUTOBOUW", instelling)
    monkeypatch.setattr(Path, "resolve", lambda self: self)        # geen echte schijf nodig
    assert moet_automatisch_bouwen(pad) is verwacht


def test_tests_bouwen_nooit_automatisch():
    assert moet_automatisch_bouwen(PROJECTMAP) is False


def test_bronnen_uit_zip_zijn_gelijk_aan_bronnen_uit_map(tmp_path, voorbeeldmap):
    """Een zip met de voorbeeldbestanden levert dezelfde namen en dezelfde spectra als de map zelf."""
    bl = laad_build_library()
    zip_pad = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_pad, "w") as z:
        for pad in sorted(voorbeeldmap.glob("*.jdx")):
            z.write(pad, f"submap/{pad.name}")                     # mappen in de zip worden genegeerd
        z.writestr("leesmij.txt", "geen spectrum")                 # en niet-.jdx-bestanden ook
    uit_map = bl.verzamel_bronnen(voorbeeldmap, tmp_path / "bestaat_niet.zip")
    uit_zip = bl.verzamel_bronnen(tmp_path / "lege_map", zip_pad)
    assert [n for n, _ in uit_map] == [n for n, _ in uit_zip] and len(uit_zip) == 10
    for (_, lees_map), (_, lees_zip) in zip(uit_map, uit_zip):
        a, b = lees_map(), lees_zip()
        assert a.titel == b.titel and (a.x == b.x).all() and (a.y == b.y).all()


def test_geen_bronnen_geeft_lege_lijst(tmp_path):
    assert laad_build_library().verzamel_bronnen(tmp_path / "leeg", tmp_path / "geen.zip") == []
