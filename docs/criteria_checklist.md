# Criteria-checklist

Alle acceptatie- en kwaliteitscriteria uit de opdracht, met per criterium: **gehaald / gedeeltelijk / niet gehaald**
en het bewijs (bestand, test of meting). Testnamen verwijzen naar `tests/`; de uitvoer van de testrun staat in
[`testresultaten.md`](testresultaten.md).

Legenda: ✅ gehaald · ⚠️ gedeeltelijk gehaald (zie toelichting) · ❌ niet gehaald

## US – Uploaden en tonen van een IR-spectrum

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| A1 | Alleen bestanden met extensie .jdx of .dx, hoofdletterongevoelig | ✅ | `test_validatie.py::test_extensie_is_hoofdletterongevoelig` (a.jdx, a.JDX, a.Jdx, a.dx, a.DX, …), `::test_kapot_2_verkeerde_extensie` (.csv, .txt, .pdf, .jdx.exe, geen extensie, .jdxx) |
| A2 | Duidelijke Nederlandse foutmelding: wat is er mis + wat moet de gebruiker doen | ✅ | `validatie.py` (`ValidatieFout` met `wat_is_er_mis` en `wat_te_doen`); `test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash` (5 soorten, via de echte app) |
| A3 | Na upload direct een grafiek, golfgetal van hoog naar laag | ✅ | `test_app.py::test_geldige_upload_toont_direct_de_grafiek`, `::test_grafiek_heeft_golfgetal_van_hoog_naar_laag_en_gemarkeerde_pieken` (x-as `autorange = reversed`); keuze transmissie/absorbantie in de zijbalk |
| K1 | Bestand tot 5 MB binnen 2 s tot de grafiek zichtbaar is; test met gegenereerd bestand van ~5 MB, tijd vastgelegd | ✅ (met kanttekening) | `test_prestatie.py::test_bestand_van_5_mb_binnen_2_seconden` en `test_app.py::test_upload_van_5_mb_in_de_app_binnen_2_seconden`. **Gemeten (bestand van 4,84 MB, 565.000 punten), laatste run: 0,38–0,45 s tot de grafiek klaar is, 0,52 s voor de hele app-run inclusief top 5** ([`testresultaten.md`](testresultaten.md) §2). **Kanttekening:** gemeten is al het werk van de server (valideren, inlezen, analyseren, zoeken, grafiek opbouwen), niet het tekenen in de browser zelf. Het tekenen in de browser is niet apart gemeten; de grafiek wordt daarvoor uitgedund tot max. 4.000 punten. Bij het ethanolvoorbeeld meldde de app in de browser 229 ms verwerkingstijd. |
| K2 | Strikte validatie (grootte, tekst, verplichte labels, datablok, numerieke data, NPOINTS); nooit crashen; ≥ 6 kapotte testbestanden | ✅ | `test_validatie.py`: de zes verplichte (`test_kapot_1` t/m `test_kapot_6`) plus o.a. NPOINTS klopt niet, afgekapt bestand, ##END vóór datablok, vermomde zip/pdf/png/exe, nulbytes, NaN/oneindig, onbekende eenheden, "zip-bom" in gecomprimeerde data, en **400 willekeurig beschadigde bestanden** (`test_willekeurig_beschadigde_bestanden_crashen_nooit`); vangnet in `valideer_upload` |
| K3 | Grafiek responsief, foutloos op desktop en tablet; beschrijven hoe gecontroleerd | ✅ (met kanttekening) | Opnieuw gecontroleerd ná de nieuwe opmaak, in de ingebouwde browser van de AI-tool met geëmuleerde schermen 1366×900 (desktop) en 768×1024 (tablet): geen horizontaal scrollen, beide grafieken (681 px op tablet), tabellen, groepvakken en statusbalk passen binnen het scherm, geen fouten in de browserconsole. Plotly `responsive: True`, `width="stretch"`. **Niet** getest op een fysieke tablet; klikken op een piek met aanraken is niet getest (de piekentabel is het alternatief). Zie [`testresultaten.md`](testresultaten.md) §3. |

## RS – Onderzoek: welke Python-bibliotheek voor JCAMP-DX?

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| A1 | Overzicht van ≥ 3 bibliotheken; chemparse controleren | ✅ | `docs/onderzoek_jcamp_bibliotheken.md` §2: jcamp, nmrglue, spectrochempy (+ eigen parser). **Correctie:** chemparse is een formule-parser en kan geen JCAMP-DX lezen (aangetoond in het testscript) |
| A2 | Testscript dat met elke bibliotheek dezelfde bestanden leest en vergelijkt (lukt het, snelheid, juistheid, transmissie/absorbantie, µm/cm⁻¹) | ✅ | `research/test_jcamp_bibliotheken.py`, uitvoer `research/resultaten/resultaten.md` |
| A3 | Onderbouwd advies | ✅ | `docs/onderzoek_jcamp_bibliotheken.md` §1 en §5: eigen parser, met `jcamp` als controle in de tests |
| K1 | Broncode en resultaten in `research/` en `docs/onderzoek_jcamp_bibliotheken.md` | ✅ | idem |
| K2 | Per bibliotheek: actief onderhouden (laatste release en commit) en Python 3.10+, in een tabel | ✅ | `docs/onderzoek_jcamp_bibliotheken.md` §3, live opgezocht met `research/onderhoud_bibliotheken.py` (uitvoer `research/resultaten/onderhoud.md`) |
| K3 | Reproduceerbaar: 5–10 voorbeeldbestanden + uitleg om de test met één commando te draaien | ✅ | `research/voorbeeldspectra/` (10 bestanden), `research/README.md` |

## LS – Leren: piekdetectie en spectra-matching

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| A1 | Theorie piekdetectie uitgelegd (Savitzky-Golay, prominence, minimale breedte, ruis via MAD, drempel als veelvoud van de ruis) | ✅ | `notebooks/piekdetectie_en_matching.ipynb` deel A (stap 1–4, met grafieken); `stofherkenner/piekdetectie.py` (uitleg bovenaan) |
| A2 | Notebook: stap voor stap ≥ 1 piek correct gedetecteerd, (a) synthetisch spectrum met bekende pieken + ruis, (b) echt spectrum met bekende piek (aceton C=O), met grafieken per stap | ✅ | Notebook (uitgevoerd, 12 grafieken): (a) alle 5 bekende pieken gevonden binnen ±8 cm⁻¹ en geen nep-pieken; (b) C=O van aceton bij 1742 cm⁻¹, ook in het micrometer/transmissie-bestand (1750 cm⁻¹) |
| A3 | `docs/theorie_matching.md`: Euclidisch, cosinus, Pearson; voor- en nadelen; keuze onderbouwd met evaluatie | ✅ | `docs/theorie_matching.md` |
| K1 | Leesbare code met duidelijke Nederlandse inline-commentaar over de piekdetectie | ✅ | `stofherkenner/piekdetectie.py` |
| K2 | Kleine functies en modules (jcamp_lezen, validatie, voorbewerking, piekdetectie, matching, functionele_groepen, app) | ✅ | `stofherkenner/` (+ `analyse.py` en `grafieken.py`), `app.py` |
| K3 | Pytest-testset: synthetische spectra (±8 cm⁻¹) en echte spectra met bekende pieken | ✅ | `tests/test_piekdetectie.py`: o.a. 10 spectra met willekeurige piekposities, ruis, spike, overlappende pieken, brede band; 14 bekende pieken in 7 echte spectra |

## Matching en evaluatie

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| M1 | Cosinus én Euclidisch (en Pearson), gevectoriseerd; zoeken door de hele bibliotheek < 1 s, gemeten | ✅ | `stofherkenner/matching.py::bereken_scores`; `test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde`; zoektijden in `docs/evaluatie.md` |
| M2 | Evaluatie: stoffen met ≥ 2 echt verschillende spectra (geen resolutie-duplicaten), leave-one-out, top-1 en top-5 per methode, aantal geteste spectra, foutvoorbeelden met verklaring; `docs/evaluatie.md` + csv | ✅ | `scripts/evaluatie.py` → `docs/evaluatie.md`, `docs/evaluatie_resultaten.csv`, `docs/evaluatie_samenvatting.csv`. 3.934 spectra van 1.735 stoffen; cosinus top-1 52,9%, top-5 69,5% |
| M3 | Standaardmethode kiezen op basis van de evaluatie | ✅ | Cosinus (`matching.STANDAARD_METHODE`), onderbouwd in `docs/evaluatie.md` en `docs/theorie_matching.md` |
| M4 | Waarschuwing bij lage beste score en bij nummers 1 en 2 dicht bij elkaar | ✅ | `matching.beoordeel_resultaat`; `test_matching.py::test_waarschuwing_bij_lage_score_en_bij_klein_verschil`; effect gemeten in `docs/evaluatie.md` |

## Functionele groepen

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| F1 | ± 8 groepen: O–H, carbonzuur, C=O, ester, N–H, C≡N, C=C, aromaat; rekening met gasfase | ✅ | `stofherkenner/functionele_groepen.py` (8 regels, gasfase-varianten voor O–H, carbonzuur, C=O/ester); `tests/test_functionele_groepen.py` |
| F2 | Bij elke regel de piek als reden + zekerheid hoog/middel/laag; bron correlatietabel | ✅ | `Bevinding.redenen`, `Bevinding.zekerheid`, `BRONVERMELDING`; getoond in de app |
| F3 | Uitleg, geen beslissing | ✅ | De top 5 komt alleen uit de matching; tekst in de app zegt dit expliciet. Kwaliteit van de regels gemeten in `docs/controle_functionele_groepen.md` |

## Database

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| D1 | `scripts/download_database.py` zoekt het IR-archief op, downloadt en pakt uit; stoppen en melden als het niet lukt | ⚠️ | Het archief bestond niet meer in de oorspronkelijke repository (verwijderd in mei 2026). **Gestopt en gemeld**; de student koos voor een oude kopie uit een fork. Het script downloadt dat archief, controleert de SHA-256 en pakt veilig uit. Zie `docs/ai_logboek.md` stap 2–3 |
| D2 | `scripts/build_library.py`: cm⁻¹ (µm omrekenen), absorbantie (%T schalen, ondergrens), raster 550–3800 / 4 cm⁻¹, normaliseren, naam/CAS/formule, onleesbare bestanden overslaan en loggen | ✅ | `scripts/build_library.py`, `stofherkenner/voorbewerking.py`; `data/build_log.txt`, `data/overgeslagen.csv` (584 overgeslagen met reden); `tests/test_voorbewerking.py` |
| D3 | Resolutie-duplicaten markeren | ✅ | Kolom `duplicaat_van` in `metadata.csv` (982 duplicaten); regels in `build_library.py` |
| D4 | Gasfase als beperking vermelden; rekening houden in de regels | ✅ | README, `docs/ethiek_en_verantwoord_gebruik.md`, `functionele_groepen.py` |
| D5 | Bronvermelding (NistChemData + NIST WebBook, onofficieel) in README en app | ✅ | README §Bronvermelding; zijbalk van de app (getest in `test_app.py::test_app_start_zonder_fouten_en_toont_disclaimer`) |

## Technische keuzes en Definition of Done

| # | Criterium | Status | Bewijs |
|---|---|---|---|
| T1 | **Python 3.10 of hoger** | ❌ / ⚠️ | De app is gebouwd en getest met **Python 3.14.7**. De vastgezette versies van numpy (2.5.5) en scipy (1.18.1) vereisen **Python 3.12+**, dus Python 3.10 en 3.11 worden **niet** ondersteund. `setup.bat` controleert dit en geeft een duidelijke melding. Oplossing (niet uitgevoerd): oudere versies vastzetten en opnieuw testen. |
| T2 | Virtual environment + `requirements.txt` met vastgezette versies | ✅ | `.venv`, `requirements.txt` (versies met `==`) |
| T3 | Streamlit + Plotly; numpy, scipy (`find_peaks`, `savgol_filter`) | ✅ | `app.py`, `grafieken.py`, `piekdetectie.py` |
| T4 | `start.bat` (dubbelklik) en `setup.bat` (venv, pakketten, database) | ✅ | `setup.bat`: getest op een schone kopie, exitcode 0 na 364 s, daarna 169 tests geslaagd (1 overgeslagen). `start.bat`: uitgevoerd vanuit de schone kopie; binnen 2 s luistert een nieuwe server op poort 8501 en de app laadt met de bibliotheek (18.016 spectra). Zie [`testresultaten.md`](testresultaten.md) §4 |
| T5 | Git-repository, commit na elke afgeronde user story | ⚠️ | Repository met een duidelijke commit per story. De eerste vier stories zijn wel pas samen gecommit (vier aparte commits om 12:39) in plaats van elk direct na afronding; zie `docs/planning_en_voortgang.md` |
| DoD1 | setup.bat en start.bat werken op een schone Windows-machine met Python 3.10+ | ⚠️ | Werkt op een schone kopie op deze Windows-computer met Python 3.14. Niet getest op een andere computer; Python 3.10/3.11 niet ondersteund (zie T1) |
| DoD2 | Alle pytest-tests slagen; uitvoer in `docs/testresultaten.md` | ✅ | **193 passed** in het hoofdproject (laatste run); [`testresultaten.md`](testresultaten.md), gemaakt met `scripts/maak_testrapport.py` |
| DoD3 | Alle criteria in deze checklist met bewijs | ✅ | dit document |
| DoD4 | Evaluatie echt gedraaid, cijfers in de documentatie | ✅ | `docs/evaluatie.md` (gemaakt door `scripts/evaluatie.py`) |

## Extra wensen van de student (na de eerste oplevering)

| # | Wens | Status | Bewijs |
|---|---|---|---|
| E1 | Opmaak in de stijl van IR-software / Windows 7-programma's | ✅ | `stijl.css` (titelbalk, groepvakken, knoppen, zijbalk, statusbalk), klassieke grafieken in `stofherkenner/grafieken.py`; `test_app.py::test_windows7_stijl_wordt_geladen`; gecontroleerd in de browser |
| E2 | Het geüploade spectrum kunnen overlayen met de top-5-stoffen | ✅ | Keuzelijst "Referenties over het spectrum leggen" (standaard nummer 1, tot alle vijf); `test_app.py::test_overlay_kan_alle_top5_stoffen_tegelijk_tonen`; in de browser gecontroleerd met alle vijf |
| E3 | Op een rode piekstip klikken en in een tabel zien welke binding het is | ✅ (met kanttekening) | `stofherkenner/piek_toewijzing.py` (correlatietabel + koppeling met de regels), `tests/test_piek_toewijzing.py`, `test_matching.py::test_pieken_uit_selectie`; in de browser geklikt op 1766 cm⁻¹ (ethylacetaat) → tabel met "Ester: C=O-rek". Kanttekening: de tabel geeft *mogelijke* bindingen (gebieden overlappen; onder 1500 cm⁻¹ staat "vingerafdrukgebied"); klikken met aanraken op een tablet is niet getest |

## Leeruitkomsten

| LU | Document | Status |
|---|---|---|
| LU1 | `docs/ai_impact_beroepspraktijk.md` | ✅ concept; **zelf aanvullen** |
| LU2 | `docs/ontwerp.md` (Mermaid), app, README, `docs/demo_script.md` | ✅ |
| LU3 | `docs/ethiek_en_verantwoord_gebruik.md` + disclaimer in de app | ✅ concept; **zelf aanvullen** |
| LU4 | `docs/ai_logboek.md` | ✅; reflectie **zelf aanvullen** |
| LU5 | `docs/planning_en_voortgang.md` + git-geschiedenis | ✅ concept; **zelf aanvullen** |
| – | `docs/bewijs_leeruitkomsten.md` met richtvragen | ✅ |
