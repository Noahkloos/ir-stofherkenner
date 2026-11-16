"""IR-Stofherkenner: de webapp (Streamlit).

Starten:  dubbelklik op start.bat   (of:  .venv\\Scripts\\streamlit run app.py)

Dit bestand regelt alleen wat er op het SCHERM komt. Het rekenwerk staat in de
map ``stofherkenner/``:
    validatie.py -> jcamp_lezen.py -> voorbewerking.py -> piekdetectie.py
    -> matching.py -> functionele_groepen.py -> piek_toewijzing.py
    (aan elkaar geknoopt in analyse.py)
De opmaak (Windows 7-stijl) staat in stijl.css.
"""

from __future__ import annotations

import html
import os
import time
from pathlib import Path

import numpy as np
import streamlit as st

from stofherkenner.analyse import Analyse, analyseer, lees_en_valideer
from stofherkenner.functionele_groepen import BRONVERMELDING
from stofherkenner.grafieken import PLOTLY_CONFIG, Referentie, overlay_grafiek, pieken_uit_selectie, spectrum_grafiek
from stofherkenner.matching import IDENTIEK_SCORE, METHODEN, STANDAARD_METHODE, Bibliotheek, laad_bibliotheek
from stofherkenner.piek_toewijzing import VERKLARING_NOTATIE, PiekRij, piekentabel
from stofherkenner.opzet import BOUWSLOT, bouw_bibliotheek, moet_automatisch_bouwen
from stofherkenner.structuren import structuur_svg
from stofherkenner.validatie import ValidatieFout
from stofherkenner.voorbewerking import RASTER, herken_y_eenheid, transmissie_als_fractie

PROJECTMAP = Path(__file__).resolve().parent
# De map met de bibliotheek. Via een omgevingsvariabele kan een test een andere map aanwijzen.
DATAMAP = Path(os.environ.get("IR_STOFHERKENNER_DATAMAP", PROJECTMAP / "data"))
VOORBEELDMAP = PROJECTMAP / "research" / "voorbeeldspectra"
STIJLBESTAND = PROJECTMAP / "stijl.css"
# Hier bewaart de app de structuurformules die hij bij NIST heeft opgehaald (niet in git).
STRUCTUURMAP = Path(os.environ.get("IR_STOFHERKENNER_STRUCTUURMAP", DATAMAP / "structuren"))

METHODE_NAMEN = {
    "cosinus": "Cosinusgelijkenis",
    "pearson": "Pearson-correlatie",
    "euclidisch": "Euclidische afstand",
}
ZEKERHEID_KLEUR = {"hoog": "green", "middel": "orange", "laag": "gray"}

st.set_page_config(page_title="IR-Stofherkenner", page_icon="🧪", layout="wide")
if STIJLBESTAND.exists():
    st.markdown(f"<style>{STIJLBESTAND.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# --- Bibliotheek laden (een keer; daarna uit het geheugen) -------------------

@st.cache_resource(show_spinner="Referentiebibliotheek laden...")
def haal_bibliotheek(datamap: str) -> Bibliotheek | None:
    """Laad de referentiebibliotheek. Geeft None als die nog niet gebouwd is."""
    map_ = Path(datamap)
    if not (map_ / "library.npz").exists() or not (map_ / "metadata.csv").exists():
        return None
    return laad_bibliotheek(map_)


# --- Kleine hulpfuncties voor het scherm ------------------------------------

def groep(sleutel: str):
    """Een "groepvak" (wit vak met een kopstrook, zoals in Windows 7). Gebruik: ``with groep("x"):``."""
    return st.container(border=True, key=f"groep_{sleutel}")


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


def toon_piekentabel(rijen: list[PiekRij]) -> None:
    """Toon pieken met hun toewijzing als nette tabel (in de stijl van een lijstweergave in Windows).

    Alle tekst gaat door html.escape, zodat een vreemde stofnaam de pagina niet kan verstoren.
    """
    if not rijen:
        st.info("Er zijn geen pieken gevonden.")
        return
    e = html.escape
    regels_html = []
    for r in rijen:
        if r.regels:
            regel_cel = "".join(
                f'<div class="w7-regel"><b>{e(t.groep)}</b><br>{e(t.kenmerk)} '
                f'<span class="w7-zekerheid w7-zekerheid-{e(t.zekerheid)}">zekerheid {e(t.zekerheid)}</span></div>'
                for t in r.regels)
        else:
            regel_cel = '<span class="w7-leeg">–</span>'
        if r.toewijzingen:
            toewijzing_cel = "<ul>" + "".join(f"<li>{e(t)}</li>" for t in r.toewijzingen) + "</ul>"
        else:
            toewijzing_cel = '<span class="w7-leeg">Geen standaardtoewijzing in de correlatietabel</span>'
        if r.vingerafdruk:
            toewijzing_cel += '<div class="w7-opmerking">Vingerafdrukgebied – toewijzing indicatief</div>'
        regels_html.append(
            f'<tr><td class="w7-getal">{r.golfgetal}</td>'
            f'<td>{e(r.intensiteit)}<br><span class="w7-klein">{r.hoogte:.2f}</span></td>'
            f'<td>{e(r.bandvorm)}<br><span class="w7-klein">{r.breedte} cm⁻¹</span></td>'
            f'<td>{regel_cel}</td><td>{toewijzing_cel}</td></tr>')
    st.markdown(
        '<div class="w7-lijst-vak"><table class="w7-lijst"><thead><tr>'
        '<th>Golfgetal<br>(cm⁻¹)</th><th>Intensiteit</th><th>Bandvorm</th>'
        '<th>Toewijzing volgens de regels</th><th>Mogelijke toewijzingen (correlatietabel)</th>'
        '</tr></thead><tbody>' + "".join(regels_html) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )


def toon_structuren(top, online: bool) -> None:
    """Structuurformules van de stoffen in de top 5, naast elkaar (op een smal scherm onder elkaar)."""
    st.markdown('<div class="w7-subkop">Structuurformules</div>', unsafe_allow_html=True)
    kolommen = st.columns(len(top))
    for kolom, r in zip(kolommen, top.itertuples()):
        with kolom:
            with st.container(border=True, key=f"structuur_{r.rang}"):
                st.markdown(f'<div class="w7-structuur-kop">#{r.rang} {html.escape(r.naam)}</div>',
                            unsafe_allow_html=True)
                svg = structuur_svg(r.nist_id, STRUCTUURMAP, online=online)
                if svg:
                    st.image(svg, width="stretch")
                else:
                    st.markdown('<div class="w7-geen-structuur">Geen structuur beschikbaar</div>',
                                unsafe_allow_html=True)
                st.caption(r.formule or "formule onbekend")
    st.caption("Structuurformules: NIST Chemistry WebBook, NIST SRD 69 (© U.S. Secretary of Commerce), getekend "
               "met RDKit. " + ("Niet in de lokale opslag? Dan wordt de structuur via internet bij NIST opgehaald; "
                                "daarbij wordt alleen het NIST-nummer van de stof verstuurd." if online else
                                "Ophalen via internet staat uit (zie zijbalk): alleen eerder opgehaalde structuren "
                                "worden getoond."))


def toon_statusbalk(delen: list[str]) -> None:
    """Statusbalk onderaan, zoals in een Windows-programma."""
    vakjes = "".join(f"<span>{html.escape(d)}</span>" for d in delen[:-1])
    vakjes += f'<span class="w7-rek">{html.escape(delen[-1])}</span>' if delen else ""
    st.markdown(f'<div class="w7-statusbalk">{vakjes}</div>', unsafe_allow_html=True)


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
    structuren_ophalen = st.checkbox(
        "Structuurformules ophalen bij NIST (internet)",
        value=True,
        help="Bij de top 5 haalt de app de structuurformule op bij het NIST Chemistry WebBook. Daarbij wordt alleen "
             "het NIST-nummer van de stof verstuurd, nooit jouw spectrum. Opgehaalde structuren worden lokaal bewaard "
             "(map data/structuren). Zet dit uit om de app volledig offline te gebruiken.",
    )
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


# --- Hoofdvenster ------------------------------------------------------------

st.title("IR-Stofherkenner")
st.markdown('<div class="w7-ondertitel">Spectrumanalyse en bibliotheekzoekfunctie voor IR-spectra (JCAMP-DX)</div>',
            unsafe_allow_html=True)
st.warning(
    "**Hulpmiddel, geen bewijs.** De uitkomst is een suggestie op basis van gelijkenis met referentiespectra. "
    "Gebruik hem nooit als enige basis om een onbekende of gevaarlijke stof te identificeren; "
    "laat de uitkomst altijd beoordelen door iemand met vakkennis en bevestig met een tweede techniek.",
    icon="⚠️",
)

if bibliotheek is None and moet_automatisch_bouwen(PROJECTMAP):
    # Op Streamlit Cloud bestaat setup.bat niet: de app bouwt de bibliotheek daar zelf, één keer.
    with st.status("Eerste start: de referentiebibliotheek wordt opgezet (± 5–10 minuten)...", expanded=True) as status:
        if not BOUWSLOT.acquire(blocking=False):
            st.write("De opbouw is al gestart door een andere bezoeker. Ververs deze pagina over een paar minuten.")
            st.stop()
        try:
            if not (DATAMAP / "library.npz").exists():
                voortgang = st.empty()

                def melding(regel: str) -> None:
                    if regel.startswith(("Stap", "Klaar", "FOUT", "Downloaden mislukt", "Bouwen mislukt")):
                        st.write(regel)                 # de belangrijke regels blijven staan
                    else:
                        voortgang.text(regel)           # voortgang (MB's, aantal bestanden) overschrijft zichzelf

                gelukt = bouw_bibliotheek(PROJECTMAP, melding)
                status.update(label="Referentiebibliotheek klaar." if gelukt else "Opzetten van de bibliotheek mislukt.",
                              state="complete" if gelukt else "error")
        finally:
            BOUWSLOT.release()
    haal_bibliotheek.clear()
    bibliotheek = haal_bibliotheek(str(DATAMAP))
    if bibliotheek is not None:
        st.rerun()

if bibliotheek is None:
    st.error("**De referentiebibliotheek is nog niet aanwezig.** Sluit de app, dubbelklik op `setup.bat` "
             "(dat downloadt en bouwt de database) en start de app daarna opnieuw. "
             "Zonder bibliotheek kun je wel een spectrum bekijken, maar niet vergelijken.")

# --- Groep: bestand openen ---------------------------------------------------
with groep("bestand"):
    st.subheader("Bestand openen")
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
    toon_statusbalk(["Gereed", "Geen bestand geopend"])
    st.stop()

# --- Stap 1: valideren en inlezen -------------------------------------------
start = time.perf_counter()
try:
    analyse = lees_en_valideer(bestandsnaam, inhoud)
except ValidatieFout as fout:
    toon_validatiefout(fout)
    toon_statusbalk(["Fout", f"Bestand afgekeurd: {bestandsnaam}"])
    st.stop()

# --- Stap 2: analyseren (mag de grafiek nooit tegenhouden) ------------------
try:
    analyse = analyseer(analyse, bibliotheek, methode, negeer_identiek=negeer_identiek)
except Exception as fout:  # vangnet: de grafiek tonen we hoe dan ook
    analyse.reden_geen_analyse = f"Er ging iets mis bij de analyse ({type(fout).__name__}). De grafiek wordt wel getoond."

rijen_pieken = piekentabel(analyse.pieken, analyse.bevindingen)

# --- Groep: spectrum met klikbare pieken ------------------------------------
spectrum = analyse.spectrum
with groep("spectrum"):
    st.subheader(f"Spectrum: {spectrum.titel}")
    details = [f"{spectrum.x.size:,} meetpunten".replace(",", "."),
               f"{analyse.golfgetal.min():.0f}–{analyse.golfgetal.max():.0f} cm⁻¹",
               f"x-as in bestand: {spectrum.x_eenheid}", f"y-as in bestand: {spectrum.y_eenheid}"]
    if spectrum.toestand:
        details.append(f"toestand: {spectrum.toestand}")
    st.caption(" · ".join(details))
    for melding in analyse.waarschuwingen:
        st.warning(melding)

    # De grafiek is klikbaar: een klik op een rode stip start de app opnieuw, met de klik in "selectie".
    # De figuur zelf mag daarbij niet veranderen, anders vergeet Streamlit de klik (zie grafieken.py).
    y_waarden, y_titel = y_voor_grafiek(analyse, weergave)
    figuur = spectrum_grafiek(analyse.golfgetal, y_waarden, y_titel, analyse.pieken,
                              losse_punten=spectrum.datablok_soort == "PEAK TABLE")
    selectie = st.plotly_chart(figuur, width="stretch", config=PLOTLY_CONFIG,
                               on_select="rerun", selection_mode="points", key=f"spectrum_{bestandsnaam}")
    tijd_tot_grafiek = (time.perf_counter() - start) * 1000
    st.caption(f"{len(analyse.pieken)} pieken gedetecteerd (rode stippen). "
               f"Verwerkt in {tijd_tot_grafiek:.0f} ms (valideren, inlezen, analyseren en grafiek opbouwen).")

    # Tabel van de aangeklikte piek(en)
    gekozen_pieken = pieken_uit_selectie(selectie, analyse.pieken)
    if gekozen_pieken:
        gekozen_afgerond = {round(g) for g in gekozen_pieken}
        st.markdown('<div class="w7-subkop">Piekinformatie – geselecteerde piek(en)</div>', unsafe_allow_html=True)
        toon_piekentabel([r for r in rijen_pieken if r.golfgetal in gekozen_afgerond])
        st.caption(f"{VERKLARING_NOTATIE}. Toewijzingen volgen standaard IR-correlatietabellen en zijn indicatief: "
                   "gebieden overlappen, en onder 1500 cm⁻¹ (vingerafdrukgebied) is een toewijzing onzeker. "
                   "'Toewijzing volgens de regels' verwijst naar het paneel met functionele groepen. "
                   "Dubbelklik op een lege plek in het spectrum om de selectie op te heffen.")
    elif analyse.pieken:
        st.caption("Selecteer een piek door op een rode markering in het spectrum te klikken; de toewijzing "
                   "verschijnt dan hier. Shift + klik selecteert meerdere pieken. Alle pieken staan ook in de "
                   "piektabel onderaan de pagina.")

if analyse.reden_geen_analyse:
    st.info(analyse.reden_geen_analyse)
    toon_statusbalk(["Gereed", bestandsnaam, f"{spectrum.x.size} punten", "Alleen grafiek getoond"])
    st.stop()

# --- Groep: top 5 ------------------------------------------------------------
if analyse.top is not None and not analyse.top.empty:
    with groep("top5"):
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
        # De structuren worden pas aan het eind van de pagina ingevuld: ophalen kan even duren,
        # en zo verschijnen grafiek, top 5, overlay en uitleg eerst.
        structuur_vak = st.container()

    # --- Groep: overlay met de top 5 -----------------------------------------
    with groep("overlay"):
        st.subheader("Overlay met de voorspelde stoffen")
        keuzes = {f"#{r.rang} {r.naam} ({r.score:.1f}%)": r for r in analyse.top.itertuples()}
        namen = list(keuzes)
        gekozen_namen = st.multiselect(
            "Referenties over het spectrum leggen",
            namen,
            default=namen[:1],
            help="Kies een of meer stoffen uit de top 5. Standaard staat alleen nummer 1 aan.",
        )
        gekozen_refs = [keuzes[n] for n in gekozen_namen]
        referenties = [
            Referentie(f"#{r.rang} {r.naam}", bibliotheek.absorbantie[r.rij_index], bibliotheek.maskers[r.rij_index] > 0)
            for r in gekozen_refs
        ]
        st.plotly_chart(
            overlay_grafiek(RASTER, analyse.voorbewerkt.absorbantie, analyse.voorbewerkt.masker, referenties),
            width="stretch", config=PLOTLY_CONFIG,
        )
        if gekozen_refs:
            st.caption("Alle spectra zijn omgerekend naar absorbantie en genormaliseerd (hoogste piek = 1). "
                       "Referenties: " + "; ".join(f"#{r.rang} gemeten als {r.fase} (NIST-bestand {r.bestand})"
                                                    for r in gekozen_refs) + ".")
        else:
            st.caption("Geen referentie gekozen: alleen het geüploade spectrum wordt getoond.")

# --- Groep: functionele groepen ---------------------------------------------
with groep("groepen"):
    st.subheader("Welke functionele groepen passen bij de pieken?")
    st.caption("Uitleg op basis van vaste regels (expertsysteem). Dit is een hulpmiddel om de top 5 te controleren, "
               "geen beslissing: de top 5 komt uit de vergelijking met de bibliotheek.")
    toon_functionele_groepen(analyse)

with st.expander("Piektabel – alle gedetecteerde pieken met toewijzing"):
    toon_piekentabel(rijen_pieken)
    st.caption(f"{VERKLARING_NOTATIE}. Bronnen correlatietabel: {BRONVERMELDING}")

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
        "5. **Uitleggen** – ALS-DAN-regels koppelen pieken aan functionele groepen; een correlatietabel geeft "
        "per piek de mogelijke bindingen.\n\n"
        "Er wordt nergens een model getraind: elke stap is een vaste, uitlegbare rekenregel."
    )
    if analyse.tijden_ms:
        st.caption("Rekentijd per stap: " + " · ".join(f"{naam}: {ms:.0f} ms" for naam, ms in analyse.tijden_ms.items()))

if analyse.top is not None and not analyse.top.empty:
    with structuur_vak:
        with st.spinner("Structuurformules laden..."):
            toon_structuren(analyse.top, online=structuren_ophalen)

status = ["Gereed", bestandsnaam, f"{spectrum.x.size} punten", f"{len(analyse.pieken)} pieken",
          f"Methode: {METHODE_NAMEN[methode]}"]
if bibliotheek is not None:
    status.append(f"Bibliotheek: {len(bibliotheek)} spectra")
toon_statusbalk(status + [f"Verwerkt in {tijd_tot_grafiek:.0f} ms"])
