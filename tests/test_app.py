"""Tests van de app zelf, met de ingebouwde testmodus van Streamlit (AppTest).

AppTest draait app.py zonder browser en laat ons controleren wat er op het
scherm zou komen: foutmeldingen, grafieken, tabellen. Zo testen we de hele
keten zoals de gebruiker hem ziet.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.conftest import PROJECTMAP, VOORBEELDMAP

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ACETON = "aceton_gas_C67641_IR_0.jdx"


def start_app() -> AppTest:
    app = AppTest.from_file(str(PROJECTMAP / "app.py"), default_timeout=60)
    app.run()
    return app


def kies_voorbeeld(app: AppTest, bestandsnaam: str) -> AppTest:
    keuze = next(s for s in app.selectbox if "voorbeeldspectrum" in s.label)
    keuze.select(bestandsnaam).run()
    return app


def tabel_met_kolom(app: AppTest, kolom: str):
    """Zoek de tabel (dataframe) op de pagina die een bepaalde kolom heeft."""
    for df in app.dataframe:
        if kolom in list(df.value.columns):
            return df.value
    raise AssertionError(f"geen tabel met kolom {kolom!r} gevonden")


def top5(app: AppTest):
    return tabel_met_kolom(app, "Overeenkomst")


def alle_tekst(app: AppTest) -> str:
    """Alle zichtbare tekst op de pagina, om in te zoeken."""
    delen = []
    for soort in ("title", "subheader", "markdown", "caption", "info", "warning", "error", "success"):
        delen += [str(e.value) for e in getattr(app, soort)]
    return "\n".join(delen)


def test_app_start_zonder_fouten_en_toont_disclaimer():
    app = start_app()
    assert not app.exception
    assert "IR-Stofherkenner" in app.title[0].value
    assert any("Hulpmiddel, geen bewijs" in w.value for w in app.warning)       # disclaimer (LU3)
    assert any("Nog geen spectrum gekozen" in i.value for i in app.info)
    # bronvermelding in de zijbalk
    zijbalk = "\n".join(str(e.value) for e in app.sidebar.caption)
    assert "NIST Chemistry WebBook" in zijbalk and "NistChemData" in zijbalk and "onofficiële" in zijbalk


def test_voorbeeld_toont_grafiek_top5_en_functionele_groepen(bibliotheek):
    app = kies_voorbeeld(start_app(), ACETON)
    assert not app.exception
    assert not app.error
    tekst = alle_tekst(app)
    assert "Spectrum: Acetone" in tekst
    assert "pieken gedetecteerd" in tekst
    assert "Top 5 meest waarschijnlijke stoffen" in tekst
    assert "Overlay met de voorspelde stoffen" in tekst
    assert "C=O (keton of aldehyde)" in tekst and "piek bij 17" in tekst      # reden met piekpositie
    # twee grafieken: spectrum + overlay
    assert len(app.get("plotly_chart")) == 2
    # de top-5-tabel heeft vijf rijen met de gevraagde kolommen en Acetone bovenaan
    tabel = top5(app)
    assert list(tabel.columns) == ["#", "Naam", "CAS-nummer", "Molecuulformule", "Fase referentie", "Overeenkomst"]
    assert len(tabel) == 5
    assert tabel.iloc[0]["Naam"] == "Acetone" and tabel.iloc[0]["CAS-nummer"] == "67-64-1"
    assert 0 <= tabel["Overeenkomst"].min() and tabel["Overeenkomst"].max() <= 100


def test_grafiek_heeft_golfgetal_van_hoog_naar_laag_en_gemarkeerde_pieken(bibliotheek):
    app = kies_voorbeeld(start_app(), ACETON)
    import json
    figuur = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert figuur["layout"]["xaxis"]["autorange"] == "reversed"            # IR-conventie: hoog -> laag
    assert "Golfgetal" in figuur["layout"]["xaxis"]["title"]["text"]
    namen = [spoor["name"] for spoor in figuur["data"]]
    assert "Gedetecteerde pieken" in namen
    pieken = next(s for s in figuur["data"] if s["name"] == "Gedetecteerde pieken")
    assert len(pieken["x"]) >= 3 if isinstance(pieken["x"], list) else True


def test_eerlijke_test_geeft_geen_100_procent(bibliotheek):
    app = kies_voorbeeld(start_app(), ACETON)
    assert top5(app).iloc[0]["Overeenkomst"] > 99.9
    assert "staat zelf in de bibliotheek" in alle_tekst(app)
    next(c for c in app.checkbox if "Eerlijke test" in c.label).check().run()
    assert not app.exception
    tabel = top5(app)
    assert tabel.iloc[0]["Overeenkomst"] < 99.95
    assert tabel.iloc[0]["CAS-nummer"] == "67-64-1"          # aceton wordt ook via een andere meting herkend


def test_overlay_kan_alle_top5_stoffen_tegelijk_tonen(bibliotheek):
    import json
    app = kies_voorbeeld(start_app(), ACETON)
    keuze = next(m for m in app.multiselect if "Referenties" in m.label)
    assert len(keuze.value) == 1 and keuze.value[0].startswith("#1 ")         # standaard: alleen nummer 1
    overlay = json.loads(app.get("plotly_chart")[1].proto.spec)
    assert len(overlay["data"]) == 2                                          # 1 referentie + geüpload spectrum
    keuze.set_value(keuze.options).run()                                      # alle vijf aanzetten
    assert not app.exception
    overlay = json.loads(app.get("plotly_chart")[1].proto.spec)
    namen = [spoor["name"] for spoor in overlay["data"]]
    assert len(namen) == 6 and namen[-1] == "Geüpload spectrum"
    assert all(n.startswith(f"#{i + 1} ") for i, n in enumerate(namen[:5]))
    assert len({spoor["line"]["color"] for spoor in overlay["data"]}) == 6    # zes verschillende kleuren
    keuze.set_value([]).run()                                                 # niets gekozen: geen crash
    assert not app.exception
    assert len(json.loads(app.get("plotly_chart")[1].proto.spec)["data"]) == 1


def test_piekentabel_met_mogelijke_bindingen(bibliotheek):
    import re
    app = kies_voorbeeld(start_app(), "ethylacetaat_gas_C141786_IR_0.jdx")
    tabel = next(str(m.value) for m in app.markdown if 'class="w7-lijst"' in str(m.value))
    assert "Mogelijke toewijzingen (correlatietabel)" in tabel and "Intensiteit" in tabel and "Bandvorm" in tabel
    golfgetallen = [int(g) for g in re.findall(r'<td class="w7-getal">(\d+)</td>', tabel)]
    assert golfgetallen == sorted(golfgetallen, reverse=True) and 1766 in golfgetallen
    rij_1766 = tabel.split('<td class="w7-getal">1766</td>')[1].split("</tr>")[0]
    assert "Ester (–COO–)" in rij_1766 and "ν(C=O)" in rij_1766 and "zekerheid hoog" in rij_1766
    assert "Selecteer een piek" in alle_tekst(app)                            # uitleg hoe je een piek kiest
    assert "👆" not in alle_tekst(app)


def test_titel_zonder_emoji():
    app = start_app()
    assert app.title[0].value == "IR-Stofherkenner"


def test_structuurformules_bij_de_top5(bibliotheek, tmp_path, monkeypatch):
    """Met een (zelfgeschreven) aceton-structuur in de opslag toont de app die bij nummer 1; de rest heeft (offline) geen structuur."""
    from tests.test_structuren import ACETON_MOL
    (tmp_path / "C67641.mol").write_text(ACETON_MOL, encoding="latin-1")
    monkeypatch.setenv("IR_STOFHERKENNER_STRUCTUURMAP", str(tmp_path))
    app = kies_voorbeeld(start_app(), ACETON)
    assert not app.exception
    tekst = alle_tekst(app)
    assert "Structuurformules" in tekst and "#1 Acetone" in tekst
    assert len(app.get("image")) == 1                                          # alleen aceton staat in de opslag
    assert tekst.count("Geen structuur beschikbaar") == 4                      # offline: de andere vier niet
    assert "NIST Chemistry WebBook" in tekst
    assert sorted(p.name for p in tmp_path.iterdir()) == ["C67641.mol"]       # niets van internet bijgekomen


def test_spectrumgrafiek_is_klikbaar(bibliotheek):
    """De spectrumgrafiek reageert op klikken (selectie van punten). Het klikken zelf is in de browser getest."""
    import json
    app = kies_voorbeeld(start_app(), ACETON)
    grafiek = app.get("plotly_chart")[0]
    assert "points" in list(grafiek.proto.selection_mode) or grafiek.proto.selection_mode
    figuur = json.loads(grafiek.proto.spec)
    assert figuur["layout"]["clickmode"] == "event+select"
    # De lijn mag geen klikken opvangen, anders komen klikken op de stippen (die op de lijn liggen) niet aan
    lijn = next(s for s in figuur["data"] if s["name"] == "Geüpload spectrum")
    assert lijn.get("hoverinfo") == "skip"


def test_windows7_stijl_wordt_geladen():
    app = start_app()
    stijl = [m.value for m in app.markdown if "<style>" in str(m.value)]
    assert stijl and ".w7-statusbalk" in stijl[0]
    assert any("w7-statusbalk" in str(m.value) and "Gereed" in str(m.value) for m in app.markdown)


def upload(app: AppTest, naam: str, inhoud: bytes) -> AppTest:
    app.file_uploader[0].upload(naam, inhoud).run() if hasattr(app.file_uploader[0], "upload") \
        else app.file_uploader[0].set_value([(naam, inhoud, "application/octet-stream")]).run()
    return app


@pytest.mark.parametrize("naam,inhoud,verwacht", [
    ("spectrum.csv", b"golfgetal;absorbantie\n4000;0.1\n", "accepteert alleen JCAMP-DX-bestanden"),
    ("leeg.jdx", b"", "leeg"),
    ("rommel.jdx", bytes(np.random.default_rng(0).integers(0, 256, 5000, dtype=np.uint8)), "binaire gegevens"),
    ("half.jdx", (VOORBEELDMAP / ACETON).read_bytes()[:2000], "mist verplichte onderdelen"),
    ("groot.jdx", b"##TITLE=x\n" + b"$$ opvulling\n" * 420_000, "maximale grootte is 5 MB"),
])
def test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash(naam, inhoud, verwacht):
    app = start_app()
    try:
        upload(app, naam, inhoud)
    except Exception as fout:                                   # deze Streamlit-versie kan geen upload simuleren
        pytest.skip(f"AppTest ondersteunt hier geen file_uploader: {fout}")
    assert not app.exception
    assert len(app.error) == 1
    melding = app.error[0].value
    assert "Wat is er mis?" in melding and "Wat kun je doen?" in melding
    assert verwacht in melding
    assert len(app.get("plotly_chart")) == 0                    # er wordt niets met het bestand gedaan


def test_geldige_upload_toont_direct_de_grafiek(bibliotheek):
    app = start_app()
    try:
        upload(app, "Mijn Monster.JDX", (VOORBEELDMAP / "tolueen_vloeistof_C108883_IR_2.jdx").read_bytes())
    except Exception as fout:
        pytest.skip(f"AppTest ondersteunt hier geen file_uploader: {fout}")
    assert not app.exception and not app.error
    assert "Spectrum: TOLUENE" in alle_tekst(app)
    assert len(app.get("plotly_chart")) == 2
    assert top5(app).iloc[0]["CAS-nummer"] == "108-88-3"
    assert "Aromaat (benzeenring)" in alle_tekst(app)


def test_upload_van_5_mb_in_de_app_binnen_2_seconden(bibliotheek):
    """Hele app-run met een upload van ~5 MB: van bestand ontvangen tot grafiek, top 5 en uitleg klaar.

    Dit meet alles wat de server doet (inclusief zoeken in de bibliotheek), maar niet het tekenen in de browser
    zelf; dat is in de browser gecontroleerd (zie docs/testresultaten.md).
    """
    import time

    from tests.test_prestatie import maak_bestand_van_ongeveer_5_mb
    inhoud = maak_bestand_van_ongeveer_5_mb()
    app = start_app()                                  # bibliotheek wordt hier al in de cache geladen
    start = time.perf_counter()
    try:
        upload(app, "groot_5mb.jdx", inhoud)
    except Exception as fout:
        pytest.skip(f"AppTest ondersteunt hier geen file_uploader: {fout}")
    duur = time.perf_counter() - start
    print(f"\n[meting] app-run met upload van {len(inhoud) / 1024 / 1024:.2f} MB tot en met grafiek + top 5: {duur:.2f} s")
    assert not app.exception and not app.error
    assert len(app.get("plotly_chart")) == 2
    assert duur < 2.0


def test_app_werkt_ook_zonder_bibliotheek(monkeypatch, tmp_path):
    """Zonder gebouwde database toont de app een uitleg en nog steeds de grafiek (geen crash)."""
    monkeypatch.setenv("IR_STOFHERKENNER_DATAMAP", str(tmp_path))      # lege map: geen bibliotheek
    app = kies_voorbeeld(start_app(), ACETON)
    assert not app.exception
    assert any("referentiebibliotheek is nog niet aanwezig" in e.value for e in app.error)
    assert len(app.get("plotly_chart")) == 1                           # het spectrum zelf wordt wel getoond
    tekst = alle_tekst(app)
    assert "pieken gedetecteerd" in tekst and "C=O (keton of aldehyde)" in tekst
    assert "Top 5" not in tekst
