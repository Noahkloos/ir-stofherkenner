"""Evaluatie: hoe vaak vindt de app de juiste stof?

Gebruik:
    python scripts/evaluatie.py

Opzet ("leave-one-out"):
1. Neem alle stoffen waarvan minstens TWEE echt verschillende spectra in de
   bibliotheek staan (resolutie-duplicaten tellen niet mee; die zijn al
   weggelaten).
2. Haal telkens een spectrum uit de bibliotheek en doe alsof het een onbekend
   monster is. Zoek ermee in de REST van de bibliotheek.
3. Staat de juiste stof op plek 1 (top-1)? Staat hij bij de eerste vijf
   stoffen (top-5)?

Dit wordt gedaan voor cosinusgelijkenis, Pearson-correlatie en Euclidische
afstand. Alle cijfers in docs/evaluatie.md komen rechtstreeks uit deze run; er
wordt niets met de hand ingevuld.

Uitvoer:
    docs/evaluatie.md                 leesbaar rapport
    docs/evaluatie_resultaten.csv     een regel per getest spectrum
    docs/evaluatie_samenvatting.csv   de hoofdcijfers per methode
"""

from __future__ import annotations

import re
import sys
import time
import zlib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECTMAP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECTMAP))

from stofherkenner.matching import KLEIN_VERSCHIL, LAGE_SCORE, METHODEN, bereken_scores, laad_bibliotheek, zoek  # noqa: E402

DOCS = PROJECTMAP / "docs"
BLOKGROOTTE = 256          # aantal vraagspectra dat we tegelijk doorrekenen (geheugen sparen)


# --- Hulpfuncties -----------------------------------------------------------

def helft_van_stof(nist_id: str) -> int:
    """Verdeel de stoffen vast in twee helften: 0 = afstelhelft, 1 = controlehelft.

    De details van de voorbewerking zijn gekozen op de afstelhelft
    (scripts/vergelijk_voorbewerking.py). De controlehelft is daarbij niet
    gebruikt (wel bij de eerste verkenning, zie docs/ai_logboek.md). De verdeling hangt alleen af van
    het NIST-ID (via een controlegetal), dus is elke keer hetzelfde.
    """
    return zlib.crc32(nist_id.encode()) % 2


def formule_naar_telling(formule: str) -> dict[str, int]:
    """'C 3 H 6 O' -> {'C': 3, 'H': 6, 'O': 1}"""
    telling: dict[str, int] = {}
    for element, aantal in re.findall(r"([A-Z][a-z]?)\s*(\d*)", formule):
        telling[element] = telling.get(element, 0) + (int(aantal) if aantal else 1)
    return telling


def soort_verwarring(formule_a: str, formule_b: str) -> str:
    """Hoe verhouden twee stoffen zich tot elkaar, op basis van de molecuulformule?"""
    a, b = formule_naar_telling(formule_a), formule_naar_telling(formule_b)
    if not a or not b:
        return "onbekend (formule ontbreekt)"
    if a == b:
        return "isomeer (zelfde molecuulformule)"
    elementen = set(a) | set(b)
    verschil = {e: a.get(e, 0) - b.get(e, 0) for e in elementen}
    andere = [e for e in elementen if e not in ("C", "H") and verschil[e] != 0]
    if not andere and verschil.get("C", 0) != 0 and verschil.get("H", 0) == 2 * verschil.get("C", 0):
        return "homologe reeks (verschilt alleen een of meer CH2-groepen)"
    if set(a) == set(b):
        return "zelfde elementen, andere aantallen"
    return "andere samenstelling"


def evalueer_methode(bib, vraag_indexen: np.ndarray, stof_nummer: np.ndarray, methode: str,
                     vraag_vectoren: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Reken voor elk vraagspectrum uit op welke plek de juiste stof eindigt.

    Normaal is het vraagspectrum gewoon het bibliotheekspectrum zelf. Met
    ``vraag_vectoren`` kun je een bewerkte versie meegeven (bijv. met extra ruis).

    Geeft per vraagspectrum terug:
      rang         : plek van de juiste stof (1 = bovenaan), geteld in STOFFEN
      score_juist  : beste score van een ander spectrum van de juiste stof
      score_ander  : beste score van enige ANDERE stof
      index_ander  : rij-index van dat beste spectrum van een andere stof
      score_tweede : score van de op een na beste stof in de ranglijst
    """
    aantal = len(vraag_indexen)
    # Kolommen sorteren op stof, zodat we per stof het maximum kunnen nemen (np.maximum.reduceat)
    kolom_volgorde = np.argsort(stof_nummer, kind="stable")
    gesorteerde_stof = stof_nummer[kolom_volgorde]
    groep_start = np.flatnonzero(np.r_[True, gesorteerde_stof[1:] != gesorteerde_stof[:-1]])
    groep_stof = gesorteerde_stof[groep_start]
    plek_van_stof = np.empty(groep_stof.max() + 1, dtype=np.int64)
    plek_van_stof[groep_stof] = np.arange(len(groep_stof))

    rang = np.zeros(aantal, dtype=np.int64)
    score_juist = np.zeros(aantal)
    score_ander = np.zeros(aantal)
    index_ander = np.zeros(aantal, dtype=np.int64)
    score_tweede = np.zeros(aantal)

    for begin in range(0, aantal, BLOKGROOTTE):
        blok = vraag_indexen[begin:begin + BLOKGROOTTE]
        vraag = bib.vectoren[blok] if vraag_vectoren is None else vraag_vectoren[begin:begin + BLOKGROOTTE]
        scores = bereken_scores(bib.vectoren, bib.maskers, bib.vectoren_kwadraat, vraag, bib.maskers[blok], methode)
        rijen = np.arange(len(blok))
        scores[rijen, blok] = -1.0                      # het spectrum zelf doet niet mee
        per_stof = np.maximum.reduceat(scores[:, kolom_volgorde], groep_start, axis=1)   # beste score per stof
        eigen_plek = plek_van_stof[stof_nummer[blok]]
        juist = per_stof[rijen, eigen_plek].copy()
        rang[begin:begin + len(blok)] = 1 + (per_stof > juist[:, None]).sum(axis=1)
        score_juist[begin:begin + len(blok)] = juist

        # Beste ANDERE stof (voor foutvoorbeelden en voor "stof niet in database")
        zonder_eigen = scores.copy()
        zonder_eigen[stof_nummer[None, :] == stof_nummer[blok][:, None]] = -1.0
        beste = zonder_eigen.argmax(axis=1)
        index_ander[begin:begin + len(blok)] = beste
        score_ander[begin:begin + len(blok)] = zonder_eigen[rijen, beste]

        # Op een na beste stof in de ranglijst (voor het verschil tussen nummer 1 en 2)
        per_stof.partition(per_stof.shape[1] - 2, axis=1)
        score_tweede[begin:begin + len(blok)] = per_stof[:, -2]

    return {"rang": rang, "score_juist": score_juist, "score_ander": score_ander,
            "index_ander": index_ander, "score_tweede": score_tweede}


def meet_zoektijd(bib, methode: str, herhalingen: int = 50) -> tuple[float, float]:
    """Meet hoe lang een zoekopdracht door de hele bibliotheek duurt (in milliseconden).

    Geeft (mediaan, maximum) terug over ``herhalingen`` willekeurige vraagspectra.
    """
    rng = np.random.default_rng(0)
    tijden = []
    for index in rng.integers(0, len(bib), size=herhalingen):
        start = time.perf_counter()
        zoek(bib, bib.absorbantie[index], bib.maskers[index] > 0, methode, top_n=5)
        tijden.append((time.perf_counter() - start) * 1000)
    return float(np.median(tijden)), float(np.max(tijden))


def procent(waarde: float) -> str:
    return f"{100 * waarde:.1f}%"


# --- Hoofdprogramma ---------------------------------------------------------

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows-console: speciale tekens niet laten crashen
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    start_totaal = time.time()
    bib = laad_bibliotheek(PROJECTMAP / "data", alleen_uniek=True)
    meta = bib.metadata
    stof_nummer = pd.factorize(meta["nist_id"])[0]
    aantal_per_stof = np.bincount(stof_nummer)
    vraag_indexen = np.flatnonzero(aantal_per_stof[stof_nummer] >= 2)
    n_vragen = len(vraag_indexen)
    n_stoffen_getest = int((aantal_per_stof >= 2).sum())
    print(f"Bibliotheek: {len(bib)} unieke spectra van {len(aantal_per_stof)} stoffen")
    print(f"Testset    : {n_vragen} spectra van {n_stoffen_getest} stoffen met >= 2 unieke spectra")

    fase = meta["fase"].to_numpy()
    vraag_fase = fase[vraag_indexen]
    # Heeft de stof nog een ANDER spectrum in dezelfde fase als het vraagspectrum?
    sleutel = pd.Series(list(zip(stof_nummer, fase)))
    aantal_zelfde_fase = sleutel.map(sleutel.value_counts()).to_numpy()
    partner_zelfde_fase = aantal_zelfde_fase[vraag_indexen] >= 2

    resultaten: dict[str, dict[str, np.ndarray]] = {}
    samenvatting = []
    for methode in METHODEN:
        t0 = time.time()
        r = evalueer_methode(bib, vraag_indexen, stof_nummer, methode)
        mediaan_ms, max_ms = meet_zoektijd(bib, methode)
        resultaten[methode] = r
        samenvatting.append({
            "methode": methode,
            "aantal_spectra": n_vragen,
            "top1": float((r["rang"] == 1).mean()),
            "top5": float((r["rang"] <= 5).mean()),
            "top1_zelfde_fase_partner": float((r["rang"][partner_zelfde_fase] == 1).mean()),
            "top1_alleen_andere_fase": float((r["rang"][~partner_zelfde_fase] == 1).mean()),
            "zoektijd_mediaan_ms": mediaan_ms,
            "zoektijd_max_ms": max_ms,
        })
        print(f"{methode:11s} top-1 {procent(samenvatting[-1]['top1'])}  top-5 {procent(samenvatting[-1]['top5'])}  "
              f"zoektijd {mediaan_ms:.1f} ms  (evaluatie {time.time() - t0:.0f} s)")

    samenvatting_df = pd.DataFrame(samenvatting)
    # Keuze: hoogste top-1. Pearson en cosinus zijn op de vergelijkingsvorm vrijwel
    # hetzelfde (het gemiddelde van een afgeleide is bijna 0); bij een verschil
    # kleiner dan 0,5 procentpunt kiezen we de eenvoudigste en snelste: cosinus.
    beste_methode = samenvatting_df.sort_values(["top1", "top5"], ascending=False).iloc[0]["methode"]
    top1_per_methode = dict(zip(samenvatting_df["methode"], samenvatting_df["top1"]))
    if top1_per_methode[beste_methode] - top1_per_methode["cosinus"] < 0.005:
        beste_methode = "cosinus"
    r = resultaten[beste_methode]
    goed = r["rang"] == 1

    # Controle op "afstellen op de testset": cijfers apart voor afstel- en controlehelft
    helft = np.array([helft_van_stof(s) for s in meta["nist_id"].to_numpy()[vraag_indexen]])
    helft_regels = []
    for nummer, naam in ((0, "afstelhelft (details van de voorbewerking hierop gekozen)"),
                         (1, "controlehelft (niet gebruikt voor de details; wel in de eerste verkenning)")):
        m = helft == nummer
        helft_regels.append(f"| {naam} | {int(m.sum())} | {procent(goed[m].mean())} | {procent((r['rang'][m] <= 5).mean())} |")

    # Staat er bij een ANDERE stof een (vrijwel) identiek spectrum in de bibliotheek?
    identiek_bij_andere_stof = r["score_ander"] >= 99.9

    # --- CSV per vraagspectrum ---
    per_spectrum = pd.DataFrame({
        "bestand": meta["bestand"].to_numpy()[vraag_indexen],
        "naam": meta["naam"].to_numpy()[vraag_indexen],
        "formule": meta["formule"].to_numpy()[vraag_indexen],
        "fase": vraag_fase,
        "ander_spectrum_in_zelfde_fase": partner_zelfde_fase,
    })
    for methode in METHODEN:
        per_spectrum[f"rang_{methode}"] = resultaten[methode]["rang"]
        per_spectrum[f"score_juiste_stof_{methode}"] = resultaten[methode]["score_juist"].round(2)
    per_spectrum[f"beste_andere_stof_{beste_methode}"] = meta["naam"].to_numpy()[r["index_ander"]]
    per_spectrum[f"formule_beste_andere_stof_{beste_methode}"] = meta["formule"].to_numpy()[r["index_ander"]]
    per_spectrum[f"score_beste_andere_stof_{beste_methode}"] = r["score_ander"].round(2)
    DOCS.mkdir(exist_ok=True)
    per_spectrum.to_csv(DOCS / "evaluatie_resultaten.csv", index=False, encoding="utf-8")
    samenvatting_df.round(4).to_csv(DOCS / "evaluatie_samenvatting.csv", index=False, encoding="utf-8")

    # --- Uitsplitsing per fase (beste methode) ---
    fase_regels = []
    for f in ["gas", "vloeistof", "oplossing", "vast", "onbekend"]:
        m = vraag_fase == f
        if m.sum():
            fase_regels.append(f"| {f} | {m.sum()} | {procent(goed[m].mean())} | {procent((r['rang'][m] <= 5).mean())} |")

    # --- Fouten analyseren (beste methode) ---
    fout_idx = np.flatnonzero(~goed)
    formules = meta["formule"].to_numpy()
    soorten = pd.Series([
        soort_verwarring(formules[vraag_indexen[i]], formules[r["index_ander"][i]]) for i in fout_idx
    ])
    soort_telling = soorten.value_counts()
    alleen_andere_fase_bij_fout = float((~partner_zelfde_fase[fout_idx]).mean()) if len(fout_idx) else 0.0

    # Voorbeelden: per soort verwarring de twee fouten met de hoogste (dus meest overtuigende) foute score
    voorbeeld_regels = []
    fouten_df = pd.DataFrame({
        "i": fout_idx,
        "soort": soorten.to_numpy(),
        "score_fout": r["score_ander"][fout_idx],
    }).sort_values("score_fout", ascending=False)
    # (identieke spectra onder een andere naam laten we hier weg; die tellen we apart)
    fouten_df = fouten_df[fouten_df["score_fout"] < 99.9]
    for soort in ["isomeer (zelfde molecuulformule)", "homologe reeks (verschilt alleen een of meer CH2-groepen)",
                  "zelfde elementen, andere aantallen", "andere samenstelling"]:
        for _, fout in fouten_df[fouten_df["soort"] == soort].head(2).iterrows():
            i = int(fout["i"])
            qi, ai = vraag_indexen[i], r["index_ander"][i]
            voorbeeld_regels.append(
                f"| {meta['naam'][qi]} ({meta['formule'][qi]}, {fase[qi]}) | {meta['naam'][ai]} ({meta['formule'][ai]}, {fase[ai]}) "
                f"| {r['score_ander'][i]:.1f}% | {r['score_juist'][i]:.1f}% | {r['rang'][i]} | {soort} |"
            )
    # Plus twee fouten waarbij de juiste stof alleen in een andere fase beschikbaar was
    fase_fouten = [i for i in fouten_df["i"] if not partner_zelfde_fase[i]][:2]
    for i in fase_fouten:
        qi, ai = vraag_indexen[i], r["index_ander"][i]
        andere_fases = sorted(set(fase[(stof_nummer == stof_nummer[qi]) & (np.arange(len(fase)) != qi)]))
        voorbeeld_regels.append(
            f"| {meta['naam'][qi]} ({meta['formule'][qi]}, {fase[qi]}) | {meta['naam'][ai]} ({meta['formule'][ai]}, {fase[ai]}) "
            f"| {r['score_ander'][i]:.1f}% | {r['score_juist'][i]:.1f}% | {r['rang'][i]} | andere fase: referentie van de juiste stof alleen als {', '.join(andere_fases)} |"
        )

    # --- Scoreverdelingen (onderbouwing van de waarschuwingsdrempels) ---
    def kwantielen(waarden: np.ndarray) -> str:
        if len(waarden) == 0:
            return "- | - | - | - | -"
        return " | ".join(f"{np.percentile(waarden, p):.1f}%" for p in (5, 25, 50, 75, 95))

    score_top1 = np.maximum(r["score_juist"], r["score_ander"])            # de score die de app op plek 1 toont
    verschil_12 = score_top1 - r["score_tweede"]
    onder_drempel_goed = float((score_top1[goed] < LAGE_SCORE).mean())
    onder_drempel_fout = float((score_top1[~goed] < LAGE_SCORE).mean())
    onder_drempel_afwezig = float((r["score_ander"] < LAGE_SCORE).mean())
    klein_goed = float((verschil_12[goed] < KLEIN_VERSCHIL).mean())
    klein_fout = float((verschil_12[~goed] < KLEIN_VERSCHIL).mean())
    een_waarschuwing_goed = float(((score_top1[goed] < LAGE_SCORE) | (verschil_12[goed] < KLEIN_VERSCHIL)).mean())
    een_waarschuwing_fout = float(((score_top1[~goed] < LAGE_SCORE) | (verschil_12[~goed] < KLEIN_VERSCHIL)).mean())

    # --- Rapport schrijven ---
    tabel_methoden = "\n".join(
        f"| {s['methode']} | {s['aantal_spectra']} | **{procent(s['top1'])}** | **{procent(s['top5'])}** | "
        f"{procent(s['top1_zelfde_fase_partner'])} | {procent(s['top1_alleen_andere_fase'])} | "
        f"{s['zoektijd_mediaan_ms']:.1f} ms | {s['zoektijd_max_ms']:.1f} ms |"
        for s in samenvatting
    )
    tabel_soorten = "\n".join(
        f"| {soort} | {aantal} | {procent(aantal / max(len(fout_idx), 1))} |" for soort, aantal in soort_telling.items()
    )
    rapport = f"""# Evaluatie van de spectra-matching

> Dit bestand is automatisch gemaakt door `scripts/evaluatie.py` op {date.today().isoformat()}.
> Alle getallen komen uit een echte run op de volledige bibliotheek; er is niets met de hand ingevuld.
> Opnieuw draaien: `.venv\\Scripts\\python scripts\\evaluatie.py`

## Opzet

- Bibliotheek: **{len(bib)} unieke spectra** van **{len(aantal_per_stof)} stoffen** (resolutie-duplicaten zijn weggelaten, zie hieronder).
- Testset: alle stoffen met minstens twee echt verschillende spectra: **{n_stoffen_getest} stoffen, {n_vragen} spectra**.
- Methode ("leave-one-out"): elk testspectrum wordt een keer uit de bibliotheek gehaald en als "onbekend monster"
  gebruikt. We zoeken ermee in de rest van de bibliotheek ({len(bib) - 1} spectra) en kijken op welke plek de juiste stof staat.
  De ranglijst telt in *stoffen*: van elke stof telt alleen het best passende spectrum.
- **Top-1** = de juiste stof staat op plek 1. **Top-5** = de juiste stof staat bij de eerste vijf.

### Waarom duplicaten weglaten?

Van sommige stoffen staat dezelfde meting meerdere keren in de NIST-data, alleen met een andere resolutie
(vooral in de reeks QUANT-IR). Als je zo'n spectrum eruit haalt, vindt de zoekactie direct zijn "tweelingbroer"
terug. Dat is geen eerlijke test: je meet dan niet of de app een stof herkent, maar of hij een kopie herkent.
Daarom is een spectrum als duplicaat gemarkeerd (en hier weggelaten) als het van dezelfde stof is én
(a) de cosinusgelijkenis met een eerder spectrum van die stof >= 0,99 is, of (b) beide uit de QUANT-IR-resolutiereeks komen.
Regel (a) is streng: ook twee onafhankelijke metingen die toevallig bijna identiek zijn vallen weg.
De cijfers hieronder zijn daardoor eerder te voorzichtig dan te rooskleurig.

## Resultaten per methode

| Methode | Geteste spectra | Top-1 | Top-5 | Top-1 als er een ander spectrum in dezelfde fase is | Top-1 als de stof alleen in een andere fase voorkomt | Zoektijd (mediaan) | Zoektijd (max) |
|---|---|---|---|---|---|---|---|
{tabel_methoden}

De zoektijd is gemeten over 50 zoekopdrachten door de hele bibliotheek ({len(bib)} spectra) op de laptop waarop
deze evaluatie is gedraaid, inclusief het maken van de top 5. De eis was: binnen 1 seconde (1000 ms).

**Gekozen standaardmethode voor de app: `{beste_methode}`.** Keuzeregel: de hoogste top-1; als het verschil met
cosinus kleiner is dan 0,5 procentpunt kiezen we cosinus, omdat die het eenvoudigst uit te leggen en het snelst is.

Alle methoden werken op de "vergelijkingsvorm" van het spectrum (logaritme + eerste afgeleide). Waarom, en hoeveel
dat scheelt ten opzichte van de kale absorbantie, staat in [vergelijking_voorbewerking.md](vergelijking_voorbewerking.md).

### Controle: is er niet "afgesteld op de testset"?

Eerlijke kanttekening: het *idee* om compressie en een afgeleide te gebruiken kwam uit een eerste verkenning op de
hele testset (zie `docs/ai_logboek.md`). Daarna is de stoffenlijst in twee vaste helften gesplitst en zijn de
*details* (soort compressie, logfactor, venster van de afgeleide) alleen op de afstelhelft gekozen. De controlehelft
is dus niet helemaal "onaangeroerd". Resultaat van `{beste_methode}` per helft:

| Deel van de testset | Aantal spectra | Top-1 | Top-5 |
|---|---|---|---|
{chr(10).join(helft_regels)}

De cijfers van de controlehelft zijn het eerlijkst. Liggen ze duidelijk lager dan die van de afstelhelft, dan zijn de
details te veel op de afstelhelft afgesteld (overfitting). Een klein verschil wijst erop dat de keuze ook voor nieuwe
stoffen werkt, maar omdat de grote ontwerpkeuze op alle data is verkend, is dit geen volledig onafhankelijke toets.

## Invloed van de fase (methode: {beste_methode})

| Fase van het testspectrum | Aantal | Top-1 | Top-5 |
|---|---|---|---|
{chr(10).join(fase_regels)}

Bij {int(partner_zelfde_fase.sum())} van de {n_vragen} testspectra bestaat er een ander spectrum van dezelfde stof in dezelfde fase;
bij de overige {int((~partner_zelfde_fase).sum())} is de juiste stof alleen in een ándere fase aanwezig (bijv. test = gas, referentie = vaste stof).
Het verschil in top-1 tussen die twee groepen (zie tabel hierboven) laat zien hoe sterk de fase het spectrum verandert.

## Analyse van de fouten (methode: {beste_methode})

Aantal testspectra waarbij een verkeerde stof op plek 1 stond: **{len(fout_idx)} van de {n_vragen}** ({procent(len(fout_idx) / n_vragen)}).
Bij {procent(alleen_andere_fase_bij_fout)} van deze fouten was de juiste stof alleen in een andere fase beschikbaar.

Opvallend: bij {int(identiek_bij_andere_stof.sum())} testspectra staat er onder de naam van een ándere stof een (vrijwel) identiek
spectrum in de bibliotheek (score >= 99,9%). Daarvan gingen er {int((identiek_bij_andere_stof & ~goed).sum())} fout. Dit zijn fouten of
dubbelingen in de brondata (bijv. hetzelfde spectrum bij twee isomeren of onder twee namen); daar kan geen enkele
zoekmethode iets aan doen.

Hoe verhoudt de foute nummer 1 zich tot de juiste stof (op basis van de molecuulformule)?

| Soort verwarring | Aantal | Aandeel van de fouten |
|---|---|---|
{tabel_soorten}

### Voorbeelden van fouten

| Testspectrum (juiste stof) | Foute nummer 1 | Score foute stof | Score juiste stof | Plek juiste stof | Verklaring |
|---|---|---|---|---|---|
{chr(10).join(voorbeeld_regels)}

Verklaring in gewone taal:
- **Isomeren** hebben dezelfde atomen en vaak dezelfde functionele groepen; hun IR-spectra verschillen dan alleen
  in details in het "fingerprint"-gebied (onder ~1500 cm⁻¹).
- **Homologe reeksen** (bijv. opeenvolgende alkanen, alcoholen of esters die alleen een CH₂-groep verschillen)
  hebben bijna hetzelfde spectrum: dezelfde groepen, alleen een iets andere verhouding C–H tegenover de rest.
- **Andere fase**: in gasfase zijn pieken smaller en verschoven en ontbreken waterstofbruggen (vrije O–H rond
  3650 cm⁻¹ in plaats van een brede band rond 3200–3550 cm⁻¹). Een gasspectrum lijkt daardoor soms meer op het
  gasspectrum van een verwante stof dan op het vloeistofspectrum van zichzelf.

## Hoe betrouwbaar is de score? (methode: {beste_methode})

Verdeling van de score (percentielen):

| Situatie | 5% | 25% | mediaan | 75% | 95% |
|---|---|---|---|---|---|
| Score op plek 1, juiste stof gevonden ({int(goed.sum())}x) | {kwantielen(score_top1[goed])} |
| Score op plek 1, verkeerde stof op plek 1 ({int((~goed).sum())}x) | {kwantielen(score_top1[~goed])} |
| Beste score als de juiste stof NIET in de bibliotheek zit (gesimuleerd, {n_vragen}x) | {kwantielen(r['score_ander'])} |
| Verschil tussen nummer 1 en 2, juiste stof gevonden | {kwantielen(verschil_12[goed])} |
| Verschil tussen nummer 1 en 2, verkeerde stof op plek 1 | {kwantielen(verschil_12[~goed])} |

De regel "stof niet in de bibliotheek" is gesimuleerd door alle spectra van de juiste stof weg te denken en te kijken
wat dan de hoogste score is.

**Belangrijkste les:** ook als de stof helemaal niet in de bibliotheek zit, vindt de app bijna altijd iets met een
hoge score. Een hoge score is dus géén bewijs dat de stof juist is.

### Waarschuwingen in de app

De app waarschuwt als de beste score lager is dan **{LAGE_SCORE:.0f}%** en als nummer 1 en 2 minder dan
**{KLEIN_VERSCHIL:.1f} procentpunt** van elkaar liggen. Gemeten effect op de testset:

| | Juiste stof op plek 1 | Verkeerde stof op plek 1 | Juiste stof niet in bibliotheek (gesimuleerd) |
|---|---|---|---|
| Waarschuwing "lage score" | {procent(onder_drempel_goed)} | {procent(onder_drempel_fout)} | {procent(onder_drempel_afwezig)} |
| Waarschuwing "nummer 1 en 2 dicht bij elkaar" | {procent(klein_goed)} | {procent(klein_fout)} | n.v.t. |
| Minstens een van beide waarschuwingen | {procent(een_waarschuwing_goed)} | {procent(een_waarschuwing_fout)} | n.v.t. |

Lees dit als: bij een verkeerd antwoord geeft de app in {procent(een_waarschuwing_fout)} van de gevallen een waarschuwing,
maar in {procent(1 - een_waarschuwing_fout)} van de foute antwoorden dus níet. En bij een goed antwoord waarschuwt de app
in {procent(een_waarschuwing_goed)} van de gevallen onterecht. De waarschuwingen helpen, maar vervangen het oordeel van de
laborant niet.

## Beperkingen van deze evaluatie

- De test gebruikt NIST-spectra als "onbekend monster". Een eigen meting (ander apparaat, ATR, vervuild monster,
  mengsel) wijkt meer af dan een tweede NIST-spectrum. In de praktijk zal de nauwkeurigheid dus lager uitvallen.
- Alleen stoffen met minstens twee verschillende spectra konden getest worden ({n_stoffen_getest} van de {len(aantal_per_stof)} stoffen).
  Dat zijn vooral bekende, veelgebruikte stoffen.
- Stoffen die niet in de bibliotheek staan kan de app per definitie niet vinden.
- De fase-indeling komt uit het vrije tekstveld `##STATE` van de bestanden en is automatisch in vijf groepen ingedeeld.

Totale rekentijd van deze evaluatie: {time.time() - start_totaal:.0f} s.
"""
    (DOCS / "evaluatie.md").write_text(rapport, encoding="utf-8")
    print(f"\nGekozen methode: {beste_methode}")
    print(f"Rapport geschreven naar {DOCS / 'evaluatie.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
