"""IR-Stofherkenner: de webapp (Streamlit).

Starten:  dubbelklik op start.bat   (of:  .venv\\Scripts\\streamlit run app.py)

Dit bestand regelt alleen wat er op het SCHERM komt. Het rekenwerk staat in de
map ``stofherkenner/``:
    validatie.py -> jcamp_lezen.py -> voorbewerking.py -> piekdetectie.py
    -> matching.py -> functionele_groepen.py        (aan elkaar geknoopt in analyse.py)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import streamlit as st

from stofherkenner.analyse import Analyse, analyseer, lees_en_valideer
from stofherkenner.functionele_groepen import BRONVERMELDING
from stofherkenner.grafieken import PLOTLY_CONFIG, overlay_grafiek, spectrum_grafiek
from stofherkenner.matching import IDENTIEK_SCORE, METHODEN, STANDAARD_METHODE, Bibliotheek, laad_bibliotheek
from stofherkenner.validatie import ValidatieFout
from stofherkenner.voorbewerking import RASTER, herken_y_eenheid, transmissie_als_fractie

PROJECTMAP = Path(__file__).resolve().parent
# De map met de bibliotheek. Via een omgevingsvariabele kan een test een andere map aanwijzen.
DATAMAP = Path(os.environ.get("IR_STOFHERKENNER_DATAMAP", PROJECTMAP / "data"))
VOORBEELDMAP = PROJECTMAP / "research" / "voorbeeldspectra"

METHODE_NAMEN = {
    "cosinus": "Cosinusgelijkenis",
    "pearson": "Pearson-correlatie",
    "euclidisch": "Euclidische afstand",
}
ZEKERHEID_KLEUR = {"hoog": "green", "middel": "orange", "laag": "gray"}

st.set_page_config(page_title="IR-Stofherkenner", page_icon="🧪", layout="wide")


# --- Bibliotheek laden (een keer; daarna uit het geheugen) -------------------

@st.cache_resource(show_spinner="Referentiebibliotheek laden...")
def haal_bibliotheek(datamap: str) -> Bibliotheek | None:
    """Laad de referentiebibliotheek. Geeft None als die nog niet gebouwd is."""
    map_ = Path(datamap)
    if not (map_ / "library.npz").exists() or not (map_ / "metadata.csv").exists():
        return None
    return laad_bibliotheek(map_)


# --- Kleine hulpfuncties voor het scherm ------------------------------------

def toon_validatiefout(fout: ValidatieFout) -> None:
    """Toon een afgekeurd bestand als nette Nederlandse melding."""
    st.error(f"**Dit bestand kan niet worden gebruikt.**\n\n"
             f"**Wat is er mis?** {fout.wat_is_er_mis}\n\n"
             f"**Wat kun je doen?** {fout.wat_te_doen}")


def y_voor_grafiek(analyse: Analyse, weergave: str) -> tuple[np.ndarray, str]:
    """Reken de y-as om naar de gekozen weergave. Geeft (waarden, as-titel) terug."""
    y = analyse.spectrum.y
    soort = herken_y_eenheid(analyse.spectrum.y_eenheid)
    if soort == "transmissie":
        t = transmissie_als_fractie(y, analyse.spectrum.y_eenheid)
        if weergave == "Absorbantie":
            return -np.log10(np.clip(t, 0.01, None)), "Absorbantie"
        return t * 100.0, "Transmissie (%)"
    if soort == "absorbantie":
        if weergave == "Transmissie (%)":
            return 100.0 * 10.0 ** (-y), "Transmissie (%)"
        return y, "Absorbantie"
    # absorptiecoefficient (NIST QUANT-IR): tonen zoals het in het bestand staat
    return y, f"Absorptiecoëfficiënt ({analyse.spectrum.y_eenheid})"


def toon_top5(analyse: Analyse, methode: str) -> None:
    """Toon de tabel met de vijf best passende stoffen."""
    tabel = analyse.top[["rang", "naam", "cas", "formule", "fase", "score"]].rename(columns={
        "rang": "#", "naam": "Naam", "cas": "CAS-nummer", "formule": "Molecuulformule",
        "fase": "Fase referentie", "score": "Overeenkomst",
    })
    tabel["CAS-nummer"] = tabel["CAS-nummer"].replace("", "onbekend")
    st.dataframe(
        tabel,
        hide_index=True,
        width="stretch",
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "Overeenkomst": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0, max_value=100,
                help=f"Overeenkomstscore volgens {METHODE_NAMEN[methode].lower()} (0–100%).",
            ),
        },
    )


def toon_functionele_groepen(analyse: Analyse) -> None:
    """Toon de bevindingen van het expertsysteem, met per groep de pieken als reden."""
    if not analyse.bevindingen:
        st.info("De regels herkennen geen van de acht functionele groepen in dit spectrum.")
        return
    for b in analyse.bevindingen:
        kleur = ZEKERHEID_KLEUR[b.zekerheid]
        with st.container(border=True):
            st.markdown(f"**{b.groep}** &nbsp; :{kleur}-badge[zekerheid: {b.zekerheid}]")
            for reden in b.redenen:
                st.markdown(f"- {reden}")
            if b.toelichting:
                st.caption(b.toelichting)


# --- Zijbalk ----------------------------------------------------------------

bibliotheek = haal_bibliotheek(str(DATAMAP))

with st.sidebar:
    st.header("Instellingen")
    methode = st.selectbox(
        "Vergelijkingsmethode",
        METHODEN,
        index=METHODEN.index(STANDAARD_METHODE),
        format_func=lambda m: METHODE_NAMEN[m] + (" (standaard)" if m == STANDAARD_METHODE else ""),
        help="Hoe de overeenkomst met elk referentiespectrum wordt berekend. De standaard is gekozen op basis van de evaluatie.",
    )
    weergave = st.radio("Y-as van de grafiek", ["Zoals in het bestand", "Absorbantie", "Transmissie (%)"])
    negeer_identiek = st.checkbox(
        "Eerlijke test: negeer identieke spectra",
        value=False,
        help="De voorbeeldbestanden staan zelf in de bibliotheek en scoren daardoor 100%. Met dit vinkje doet het "
             "identieke referentiespectrum niet mee, zodat je ziet of de app de stof ook herkent aan een ANDERE meting.",
    )
    st.divider()
    st.subheader("Over deze app")
    if bibliotheek is not None:
        st.write(f"Referentiebibliotheek: **{len(bibliotheek):,}** spectra van "
                 f"**{bibliotheek.metadata['nist_id'].nunique():,}** stoffen.".replace(",", "."))
    st.caption(
        "Deze app gebruikt klassieke (symbolische) AI: piekdetectie met vaste rekenregels, een expertsysteem "
        "met ALS-DAN-regels en een zoekactie op gelijkenis. Er is geen model getraind."
    )
    st.caption(
        "**Bron van de referentiespectra:** NIST Chemistry WebBook, NIST Standard Reference Database 69 "
        "(© U.S. Secretary of Commerce), verzameld via NistChemData van I. Chernyshov. "
        "NistChemData is een onofficiële verzameling en geen product van NIST."
    )


# --- Hoofdpagina -------------------------------------------------------------

st.title("🧪 IR-Stofherkenner")
st.write("Upload een IR-spectrum (JCAMP-DX). De app toont het spectrum, zoekt de best passende stoffen in een "
         "bibliotheek van NIST-referentiespectra en legt uit welke functionele groepen de pieken doen vermoeden.")
st.warning(
    "**Hulpmiddel, geen bewijs.** De uitkomst is een suggestie op basis van gelijkenis met referentiespectra. "
    "Gebruik hem nooit als enige basis om een onbekende of gevaarlijke stof te identificeren; "
    "laat de uitkomst altijd beoordelen door iemand met vakkennis en bevestig met een tweede techniek.",
    icon="⚠️",
)

if bibliotheek is None:
    st.error("**De referentiebibliotheek is nog niet aanwezig.** Sluit de app, dubbelklik op `setup.bat` "
             "(dat downloadt en bouwt de database) en start de app daarna opnieuw. "
             "Zonder bibliotheek kun je wel een spectrum bekijken, maar niet vergelijken.")

kolom_upload, kolom_voorbeeld = st.columns([3, 2])
with kolom_upload:
    # type=None: we controleren de extensie ZELF, zodat we een duidelijke Nederlandse melding kunnen geven.
    upload = st.file_uploader(
        "Kies een JCAMP-DX-bestand (.jdx of .dx, maximaal 5 MB)",
        type=None,
        help="Exporteer het spectrum in de software van de spectrometer als JCAMP-DX.",
    )
with kolom_voorbeeld:
    voorbeelden = sorted(p.name for p in VOORBEELDMAP.glob("*.jdx")) if VOORBEELDMAP.exists() else []
    voorbeeld = st.selectbox(
        "...of probeer een voorbeeldspectrum",
        ["(geen)"] + voorbeelden,
        help="Voorbeeldbestanden uit de NIST-data, meegeleverd in research/voorbeeldspectra.",
    )

if upload is not None:
    bestandsnaam, inhoud = upload.name, upload.getvalue()
elif voorbeeld != "(geen)":
    bestandsnaam, inhoud = voorbeeld, (VOORBEELDMAP / voorbeeld).read_bytes()
else:
    st.info("Nog geen spectrum gekozen. Upload een bestand of kies een voorbeeld.")
    st.stop()

# --- Stap 1: valideren en inlezen -------------------------------------------
start = time.perf_counter()
try:
    analyse = lees_en_valideer(bestandsnaam, inhoud)
except ValidatieFout as fout:
    toon_validatiefout(fout)
    st.stop()

# --- Stap 2: analyseren (mag de grafiek nooit tegenhouden) ------------------
try:
    analyse = analyseer(analyse, bibliotheek, methode, negeer_identiek=negeer_identiek)
except Exception as fout:  # vangnet: de grafiek tonen we hoe dan ook
    analyse.reden_geen_analyse = f"Er ging iets mis bij de analyse ({type(fout).__name__}). De grafiek wordt wel getoond."

# --- Stap 3: grafiek van het spectrum ---------------------------------------
spectrum = analyse.spectrum
st.subheader(f"Spectrum: {spectrum.titel}")
details = [f"{spectrum.x.size:,} meetpunten".replace(",", "."),
           f"{analyse.golfgetal.min():.0f}–{analyse.golfgetal.max():.0f} cm⁻¹",
           f"x-as in bestand: {spectrum.x_eenheid}", f"y-as in bestand: {spectrum.y_eenheid}"]
if spectrum.toestand:
    details.append(f"toestand: {spectrum.toestand}")
st.caption(" · ".join(details))
for melding in analyse.waarschuwingen:
    st.warning(melding)

y_waarden, y_titel = y_voor_grafiek(analyse, weergave)
figuur = spectrum_grafiek(analyse.golfgetal, y_waarden, y_titel, analyse.pieken,
                          losse_punten=spectrum.datablok_soort == "PEAK TABLE")
st.plotly_chart(figuur, width="stretch", config=PLOTLY_CONFIG)
tijd_tot_grafiek = (time.perf_counter() - start) * 1000
st.caption(f"{len(analyse.pieken)} pieken gedetecteerd (rode stippen). "
           f"Verwerkt in {tijd_tot_grafiek:.0f} ms (valideren, inlezen, analyseren en grafiek opbouwen).")

if analyse.reden_geen_analyse:
    st.info(analyse.reden_geen_analyse)
    st.stop()

# --- Stap 4: top 5 ----------------------------------------------------------
if analyse.top is not None and not analyse.top.empty:
    st.subheader("Top 5 meest waarschijnlijke stoffen")
    if negeer_identiek:
        st.info("Eerlijke test staat aan: referentiespectra die identiek zijn aan dit spectrum doen niet mee.")
    elif float(analyse.top.iloc[0]["score"]) >= IDENTIEK_SCORE:
        st.info("Dit exacte spectrum staat zelf in de bibliotheek; daarom is de score 100%. Zet in de zijbalk "
                "'Eerlijke test' aan om te zien of de stof ook via een ándere meting wordt herkend.")
    for melding in analyse.zoek_waarschuwingen:
        st.warning(melding, icon="⚠️")
    toon_top5(analyse, methode)
    st.caption(f"Methode: {METHODE_NAMEN[methode]}. Van elke stof telt het best passende referentiespectrum. "
               "Een hoge score betekent 'lijkt sterk op dit referentiespectrum', niet 'is bewezen deze stof'.")

    # --- Stap 5: referentie over het spectrum heen ---------------------------
    st.subheader("Visuele vergelijking met een referentiespectrum")
    keuzes = {f"#{r.rang}  {r.naam}  ({r.score:.1f}%)": r for r in analyse.top.itertuples()}
    gekozen = keuzes[st.selectbox("Referentie om te vergelijken", list(keuzes), index=0)]
    referentie = bibliotheek.absorbantie[gekozen.rij_index]
    referentie_masker = bibliotheek.maskers[gekozen.rij_index] > 0
    st.plotly_chart(
        overlay_grafiek(RASTER, analyse.voorbewerkt.absorbantie, analyse.voorbewerkt.masker,
                        referentie, referentie_masker, gekozen.naam),
        width="stretch", config=PLOTLY_CONFIG,
    )
    st.caption(f"Beide spectra zijn omgerekend naar absorbantie en genormaliseerd (hoogste piek = 1). "
               f"Referentie gemeten als: {gekozen.fase} (NIST-bestand {gekozen.bestand}).")

# --- Stap 6: functionele groepen --------------------------------------------
st.subheader("Welke functionele groepen passen bij de pieken?")
st.caption("Uitleg op basis van vaste regels (expertsysteem). Dit is een hulpmiddel om de top 5 te controleren, "
           "geen beslissing: de top 5 komt uit de vergelijking met de bibliotheek.")
toon_functionele_groepen(analyse)

with st.expander("Alle gedetecteerde pieken"):
    st.dataframe(
        [{"Golfgetal (cm⁻¹)": round(p.golfgetal), "Relatieve hoogte": round(p.hoogte, 2),
          "Prominentie": round(p.prominentie, 2), "Breedte (cm⁻¹)": round(p.breedte)} for p in analyse.pieken],
        hide_index=True, width="stretch",
    )

with st.expander("Hoe komt de app tot dit resultaat?"):
    st.markdown(
        "1. **Controleren en inlezen** – het bestand wordt streng gecontroleerd op het JCAMP-DX-formaat.\n"
        "2. **Voorbewerken** – x-as naar cm⁻¹, y-as naar absorbantie, op een vast raster van 4 cm⁻¹ "
        "(550–3800 cm⁻¹), basislijn op 0 en hoogste piek op 1.\n"
        "3. **Pieken zoeken** – gladmaken (Savitzky-Golay), ruis schatten (MAD) en alleen pieken houden die "
        "duidelijk boven de ruis uitsteken en breed genoeg zijn.\n"
        "4. **Vergelijken** – het spectrum wordt met elk referentiespectrum vergeleken. Daarvoor worden de "
        "piekhoogtes logaritmisch samengedrukt en wordt de helling (afgeleide) vergeleken, zodat piekposities "
        "zwaarder tellen dan piekhoogtes en de basislijn wegvalt.\n"
        "5. **Uitleggen** – ALS-DAN-regels koppelen pieken aan functionele groepen.\n\n"
        "Er wordt nergens een model getraind: elke stap is een vaste, uitlegbare rekenregel."
    )
    if analyse.tijden_ms:
        st.caption("Rekentijd per stap: " + " · ".join(f"{naam}: {ms:.0f} ms" for naam, ms in analyse.tijden_ms.items()))
    st.caption(BRONVERMELDING)
