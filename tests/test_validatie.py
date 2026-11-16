"""Tests voor de strenge bestandscontrole (US, kwaliteitscriterium 2).

Kern: kapotte of kwaadaardige bestanden mogen de app NOOIT laten crashen. Ze
moeten altijd een ``ValidatieFout`` met Nederlandse uitleg opleveren.
"""

from __future__ import annotations

import numpy as np
import pytest

from stofherkenner.validatie import MAX_BESTANDSGROOTTE, ValidatieFout, valideer_upload
from tests.conftest import gauss, maak_jcamp


def verwacht_fout(bestandsnaam: str, inhoud: bytes, code: str) -> ValidatieFout:
    """Controleer dat het bestand wordt afgekeurd met de verwachte foutcode en een bruikbare melding."""
    with pytest.raises(ValidatieFout) as info:
        valideer_upload(bestandsnaam, inhoud)
    fout = info.value
    assert fout.code == code, f"verwachtte code {code!r}, kreeg {fout.code!r}: {fout.wat_is_er_mis}"
    assert len(fout.wat_is_er_mis) > 15, "de melding moet uitleggen wat er mis is"
    assert len(fout.wat_te_doen) > 15, "de melding moet uitleggen wat de gebruiker moet doen"
    return fout


# --- Geldige bestanden worden geaccepteerd ----------------------------------

def test_geldig_bestand_wordt_geaccepteerd(geldig_bestand):
    resultaat = valideer_upload("monster.jdx", geldig_bestand)
    assert resultaat.spectrum.titel == "Testspectrum"
    assert resultaat.spectrum.x.size == 1751


@pytest.mark.parametrize("naam", ["a.jdx", "a.JDX", "a.Jdx", "a.dx", "a.DX", "mijn spectrum.v2.jdx"])
def test_extensie_is_hoofdletterongevoelig(geldig_bestand, naam):
    assert valideer_upload(naam, geldig_bestand).spectrum.x.size > 0


def test_alle_voorbeeldspectra_zijn_geldig(voorbeeldmap):
    bestanden = sorted(voorbeeldmap.glob("*.jdx"))
    assert len(bestanden) >= 5
    for pad in bestanden:
        resultaat = valideer_upload(pad.name, pad.read_bytes())
        assert resultaat.spectrum.x.size > 100, pad.name


def test_windows_regeleindes_en_bom_zijn_geen_probleem(geldig_bestand):
    inhoud = b"\xef\xbb\xbf" + geldig_bestand.replace(b"\n", b"\r\n")
    assert valideer_upload("monster.jdx", inhoud).spectrum.x.size == 1751


# --- De zes verplichte kapotte bestanden ------------------------------------

def test_kapot_1_leeg_bestand():
    verwacht_fout("leeg.jdx", b"", "leeg")


@pytest.mark.parametrize("naam", ["spectrum.csv", "spectrum.txt", "spectrum.pdf", "spectrum.jdx.exe", "spectrum", "spectrum.jdxx"])
def test_kapot_2_verkeerde_extensie(geldig_bestand, naam):
    fout = verwacht_fout(naam, geldig_bestand, "extensie")
    assert ".jdx" in fout.wat_is_er_mis


def test_kapot_3_binaire_rommel():
    rommel = np.random.default_rng(0).integers(0, 256, size=20_000, dtype=np.uint8).tobytes()
    verwacht_fout("rommel.jdx", rommel, "binair")


def test_kapot_4_ontbrekende_labels(geldig_bestand):
    for label in ("##JCAMP-DX", "##XUNITS", "##YUNITS", "##END", "##XYDATA"):
        tekst = "\n".join(r for r in geldig_bestand.decode().splitlines() if not r.startswith(label))
        fout = verwacht_fout("monster.jdx", tekst.encode(), "ontbrekende_labels")
        assert label.lstrip("#").split("=")[0] in fout.wat_is_er_mis or "datablok" in fout.wat_is_er_mis


def test_kapot_5_onzin_in_datablok(geldig_bestand):
    regels = geldig_bestand.decode().splitlines()
    start = next(i for i, r in enumerate(regels) if r.startswith("##XYDATA"))
    regels[start + 3] = "dit is <geen> getal !!!"
    verwacht_fout("monster.jdx", "\n".join(regels).encode(), "data_onleesbaar")


def test_kapot_6_te_groot_bestand(geldig_bestand):
    te_groot = geldig_bestand + b"$$ opvulling\n" * (MAX_BESTANDSGROOTTE // 13 + 10)
    assert len(te_groot) > MAX_BESTANDSGROOTTE
    fout = verwacht_fout("groot.jdx", te_groot, "te_groot")
    assert "5 MB" in fout.wat_is_er_mis


# --- Nog meer kapotte bestanden ---------------------------------------------

def test_npoints_klopt_niet():
    x = np.arange(500.0, 4000.0, 4.0)
    tekst = maak_jcamp(x, gauss(x, 1700, 1, 10), npoints=len(x) + 25)
    fout = verwacht_fout("monster.jdx", tekst.encode(), "npoints")
    assert str(len(x)) in fout.wat_is_er_mis


def test_afgekapt_bestand_wordt_afgekeurd(geldig_bestand):
    """Een half geupload bestand: de laatste helft (inclusief ##END) ontbreekt."""
    verwacht_fout("monster.jdx", geldig_bestand[: len(geldig_bestand) // 2], "ontbrekende_labels")


def test_end_voor_het_datablok(geldig_bestand):
    tekst = geldig_bestand.decode().replace("##END=", "").replace("##XYDATA", "##END=\n##XYDATA")
    verwacht_fout("monster.jdx", tekst.encode(), "ontbrekende_labels")


def test_geen_jcamp_maar_gewone_tekst():
    verwacht_fout("brief.jdx", b"Beste laborant,\nhierbij het spectrum.\nGroet!\n", "geen_jcamp")


def test_csv_met_jdx_extensie():
    verwacht_fout("data.jdx", b"golfgetal;absorbantie\n4000;0.01\n3998;0.02\n", "geen_jcamp")


@pytest.mark.parametrize("begin", [b"PK\x03\x04", b"%PDF-1.7\n", b"\x89PNG\r\n\x1a\n", b"MZ\x90\x00"])
def test_vermomd_binair_bestand(begin):
    """Een zip, pdf, png of exe met de extensie .jdx."""
    verwacht_fout("vermomd.jdx", begin + b"\x00\x01\x02" * 500, "binair")


def test_nulbytes_midden_in_tekst(geldig_bestand):
    verwacht_fout("monster.jdx", geldig_bestand[:300] + b"\x00\x00\x00" + geldig_bestand[300:], "binair")


def test_leeg_datablok(geldig_bestand):
    regels = [r for r in geldig_bestand.decode().splitlines() if r.startswith("##")]
    verwacht_fout("monster.jdx", "\n".join(regels).encode(), "geen_data")


def test_nan_en_oneindig_in_data(geldig_bestand):
    for kwaad in ("nan", "inf", "1e999"):
        regels = geldig_bestand.decode().splitlines()
        start = next(i for i, r in enumerate(regels) if r.startswith("##XYDATA"))
        delen = regels[start + 2].split()
        delen[3] = kwaad
        regels[start + 2] = " ".join(delen)
        verwacht_fout("monster.jdx", "\n".join(regels).encode(), "data_onleesbaar")


def test_onbekende_eenheden():
    x = np.arange(500.0, 4000.0, 4.0)
    y = gauss(x, 1700, 1, 10)
    verwacht_fout("m.jdx", maak_jcamp(x, y, x_eenheid="SECONDS").encode(), "eenheid")
    verwacht_fout("m.jdx", maak_jcamp(x, y, y_eenheid="Reflectance").encode(), "eenheid")


def test_te_weinig_punten():
    tekst = "##TITLE=x\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n##NPOINTS=1\n##XYDATA=(X++(Y..Y))\n500 1\n##END=\n"
    verwacht_fout("m.jdx", tekst.encode(), "data_onleesbaar")


def test_html_en_script_in_titel_is_gewoon_tekst():
    """Een 'kwaadaardige' titel mag niets stukmaken; hij wordt als gewone tekst ingelezen."""
    x = np.arange(500.0, 4000.0, 4.0)
    tekst = maak_jcamp(x, gauss(x, 1700, 1, 10), titel="<script>alert('x')</script>")
    assert valideer_upload("m.jdx", tekst.encode()).spectrum.titel.startswith("<script>")


def test_enorm_herhaalgetal_in_gecomprimeerde_data_blaast_geheugen_niet_op():
    """ASDF-'herhaal'-tekens met een absurd groot getal (een soort zip-bom) worden geweigerd."""
    tekst = ("##TITLE=bom\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n"
             "##FIRSTX=500\n##LASTX=4000\n##XYDATA=(X++(Y..Y))\n500A0S999999999\n##END=\n")
    verwacht_fout("bom.jdx", tekst.encode(), "data_onleesbaar")


# --- "Fuzzing": honderden willekeurig beschadigde bestanden -----------------

def test_willekeurig_beschadigde_bestanden_crashen_nooit(geldig_bestand, voorbeeldmap):
    """Beschadig echte bestanden op 400 willekeurige manieren.

    Elke uitkomst is goed, behalve een crash: het bestand wordt ofwel
    geaccepteerd, ofwel netjes afgekeurd met een ValidatieFout.
    """
    rng = np.random.default_rng(42)
    bronnen = [geldig_bestand] + [p.read_bytes() for p in sorted(voorbeeldmap.glob("*.jdx"))[:3]]
    afgekeurd = 0
    for i in range(400):
        data = bytearray(bronnen[i % len(bronnen)])
        soort = i % 4
        if soort == 0:        # willekeurige bytes overschrijven
            for plek in rng.integers(0, len(data), size=rng.integers(1, 30)):
                data[plek] = rng.integers(0, 256)
        elif soort == 1:      # afkappen op een willekeurige plek
            data = data[: rng.integers(0, len(data))]
        elif soort == 2:      # een willekeurig stuk eruit knippen
            a, b = sorted(rng.integers(0, len(data), size=2))
            data = data[:a] + data[b:]
        else:                 # een willekeurig stuk verdubbelen
            a, b = sorted(rng.integers(0, len(data), size=2))
            data = data[:b] + data[a:b] + data[b:]
        try:
            valideer_upload("fuzz.jdx", bytes(data))
        except ValidatieFout as fout:
            afgekeurd += 1
            assert fout.code != "onbekend", f"onverwachte fout in het vangnet bij variant {i}: {fout.wat_is_er_mis}"
    assert afgekeurd > 100      # de meeste beschadigingen moeten opgemerkt worden
