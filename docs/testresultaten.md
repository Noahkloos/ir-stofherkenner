# Testresultaten

Alle uitvoer hieronder komt uit echte runs. Pytest-deel gemaakt door `scripts/maak_testrapport.py` op
2026-11-16 (Windows 10, Python 3.14.7). Opnieuw maken:
`.venv\Scripts\python scripts\maak_testrapport.py`

## 1. Pytest: alle tests

**Resultaat: 193 passed in 15.12s.**

| Testbestand | Aantal | Geslaagd | Wat wordt getest |
|---|---|---|---|
| `test_app.py` | 16 | 16 | De app zelf (Streamlit AppTest): disclaimer, stijl, grafieken, top 5, overlay met meerdere referenties, piekentabel, uploads, eerlijke test, zonder bibliotheek, 5 MB |
| `test_functionele_groepen.py` | 29 | 29 | Expertsysteem: elke regel los en op echte spectra; geen stellige valse meldingen |
| `test_jcamp_lezen.py` | 11 | 11 | Parser: kop, factoren, micrometer, gecomprimeerde data, meerdere blokken; vergelijking met jcamp |
| `test_matching.py` | 22 | 22 | Cosinus/Pearson/Euclidisch, maskers, zoeken, waarschuwingen, snelheid; vertaling van een klik naar een piek |
| `test_piek_toewijzing.py` | 17 | 17 | Welke binding hoort bij een piek: correlatietabel, breedte en hoogte, koppeling met de regels |
| `test_piekdetectie.py` | 34 | 34 | Synthetische spectra (bekende pieken ±8 cm⁻¹, ruis, spike, overlap) en 14 bekende pieken in echte spectra |
| `test_prestatie.py` | 3 | 3 | Bestand van ~5 MB binnen 2 s; uitdunnen grafiek; te groot bestand snel afgewezen |
| `test_validatie.py` | 37 | 37 | De zes verplichte kapotte bestanden, een reeks andere kapotte bestanden en 400 willekeurig beschadigde bestanden |
| `test_voorbewerking.py` | 24 | 24 | Eenheden, omrekenen µm→cm⁻¹ en T→A, raster, resolutie, normaliseren, vergelijkingsvorm |

## 2. Metingen (uitvoer van `pytest -s`)

```
[meting] app-run met upload van 4.84 MB tot en met grafiek + top 5: 0.52 s
[meting] zoeken (cosinus) door 18016 spectra: 22 ms
[meting] zoeken (pearson) door 18016 spectra: 34 ms
[meting] zoeken (euclidisch) door 18016 spectra: 23 ms
[meting] bestand van 4.84 MB, 565000 meetpunten: valideren + inlezen + analyseren + grafiek in 0.38 s (snelste) / 0.45 s (langzaamste van 3)
```

- **Eis US-K1 (≤ 2 s tot de grafiek bij 5 MB):** gehaald, zie de metingen hierboven. Gemeten is al het werk van de
  server: valideren, inlezen, voorbewerken, pieken zoeken, functionele groepen en de grafiek opbouwen
  (`test_prestatie.py`), en bij de app-run ook het zoeken in de bibliotheek en de top 5 (`test_app.py`).
  Niet apart gemeten: het tekenen in de browser. De grafiek wordt daarvoor uitgedund tot maximaal 4.000 punten.
- **Eis matching (< 1 s door de hele bibliotheek):** gehaald, zie de zoektijden hierboven.

## 3. Controle in de browser (desktop en tablet)

Laatst gecontroleerd op 16 november 2026, ná de aanpassingen aan de opmaak (Windows 7-stijl), de overlay met de
top 5 en de klikbare pieken. Gecontroleerd in de ingebouwde browser van de AI-tool (Chromium), met geëmuleerde
schermen, gemeten met JavaScript in de pagina:

| Scherm (geëmuleerd) | Voorbeeld | Horizontaal scrollen? | Grafieken | Groepvakken / statusbalk | Fouten in de console |
|---|---|---|---|---|---|
| Desktop 1366 × 900 | ethylacetaat | nee | passen binnen het scherm | passen | geen |
| Tablet 768 × 1024 | tolueen | nee | 681 px breed, binnen het scherm | 725 px, binnen het scherm | geen |

Verder in de browser gecontroleerd:
- **Klikken op een rode stip** (ethylacetaat, piek bij 1766 cm⁻¹): de tabel "Aangeklikte piek(en)" verschijnt met
  "Ester (–COO–): C=O-rek (ester)" in de kolom "Volgens de regels". In Plotly zelf is gemeten dat de klik als
  selectie binnenkomt (`plotly_selected`, spoor 1, x = 1766).
  Let op: Plotly herkent een klik pas als de muis even boven de stip heeft gestaan (het gele infovakje verschijnt).
  Bij een gewone muis gebeurt dat vanzelf. **Op een echte tablet (aanraken) is klikken niet getest**; daarvoor is er
  de piekentabel onderaan met alle pieken.
- **Overlay**: met alle vijf stoffen gekozen toont de grafiek zes lijnen (vijf referenties en het geüploade spectrum),
  elk in een eigen kleur.
- **Pictogrammen**: de pictogrammen (bijv. op de uploadknop) worden als pictogram getoond, niet als tekst.

**Beperking:** geëmuleerde schermen, geen fysieke tablet.

## 4. setup.bat en start.bat op een schone kopie

Gedaan vóór de aanpassingen aan de opmaak; `setup.bat` en `start.bat` zijn daarna niet veranderd.
De repository is gekloond naar een lege map (met een spatie in het pad: `...\schone test\ir-stofherkenner`), zonder
`.venv` en zonder `data/`.

| Stap | Resultaat |
|---|---|
| `setup.bat` | **Exitcode 0 na 364 s.** Venv aangemaakt, pakketten geïnstalleerd, `nist_IR.zip` gedownload en SHA-256 gecontroleerd, 19.582 bestanden uitgepakt, bibliotheek gebouwd: 18.998 spectra, 982 duplicaten, 584 overgeslagen (identiek aan het hoofdproject) |
| Tests in de schone kopie | **169 passed, 1 skipped** (versie van dat moment). De overgeslagen test vergelijkt met de bibliotheek `jcamp`, die alleen voor het onderzoek nodig is |
| Startcommando (poort 8502) | Antwoordt binnen 2 s (`/_stcore/health` = ok), zonder vraag om een e-mailadres (headless) |
| `start.bat` (poort 8501) | Uitgevoerd vanuit de schone kopie nadat de oude testservers (met toestemming van de student) waren gestopt: binnen 2 s luistert een **nieuw** proces op poort 8501. In de browser laadt de app met "Referentiebibliotheek: 18.016 spectra van 15.817 stoffen" |

**Kanttekeningen:**
- Dit is een schone *kopie* op dezelfde computer, geen schone *computer*: Python 3.14 was al geïnstalleerd en er
  kunnen pakketten in de pip-cache hebben gestaan.
- Bij `start.bat` is niet automatisch gecontroleerd of er ook echt een browsertabblad opengaat, en de foutmeldingen
  bovenin `start.bat` (als de venv of de bibliotheek ontbreekt) zijn niet getest.
- Python 3.10/3.11 is niet getest en wordt niet ondersteund (zie `docs/criteria_checklist.md`, T1).

## 5. Volledige pytest-uitvoer

```
platform win32 -- Python 3.14.7, pytest-9.2.0, pluggy-1.7.0 -- C:\claude code\ir-stofherkenner\.venv\Scripts\python.exe
rootdir: C:\claude code\ir-stofherkenner
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.14.5

tests/test_app.py::test_app_start_zonder_fouten_en_toont_disclaimer PASSED [  0%]
tests/test_app.py::test_voorbeeld_toont_grafiek_top5_en_functionele_groepen PASSED [  1%]
tests/test_app.py::test_grafiek_heeft_golfgetal_van_hoog_naar_laag_en_gemarkeerde_pieken PASSED [  1%]
tests/test_app.py::test_eerlijke_test_geeft_geen_100_procent PASSED      [  2%]
tests/test_app.py::test_overlay_kan_alle_top5_stoffen_tegelijk_tonen PASSED [  2%]
tests/test_app.py::test_piekentabel_met_mogelijke_bindingen PASSED       [  3%]
tests/test_app.py::test_spectrumgrafiek_is_klikbaar PASSED               [  3%]
tests/test_app.py::test_windows7_stijl_wordt_geladen PASSED              [  4%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[spectrum.csv-golfgetal;absorbantie\n4000;0.1\n-accepteert alleen JCAMP-DX-bestanden] PASSED [  4%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[leeg.jdx--leeg] PASSED [  5%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[rommel.jdx-inhoud2-binaire gegevens] PASSED [  5%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[half.jdx-inhoud3-mist verplichte onderdelen] PASSED [  6%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[groot.jdx-inhoud4-maximale grootte is 5 MB] PASSED [  6%]
tests/test_app.py::test_geldige_upload_toont_direct_de_grafiek PASSED    [  7%]
tests/test_app.py::test_upload_van_5_mb_in_de_app_binnen_2_seconden PASSED [  7%]
tests/test_app.py::test_app_werkt_ook_zonder_bibliotheek PASSED          [  8%]
tests/test_functionele_groepen.py::test_er_zijn_acht_regels PASSED       [  8%]
tests/test_functionele_groepen.py::test_geen_pieken_geen_bevindingen PASSED [  9%]
tests/test_functionele_groepen.py::test_alcohol_vloeistof_brede_band PASSED [  9%]
tests/test_functionele_groepen.py::test_alcohol_gasfase_smalle_vrije_oh PASSED [ 10%]
tests/test_functionele_groepen.py::test_smalle_piek_bij_3400_is_geen_alcohol PASSED [ 10%]
tests/test_functionele_groepen.py::test_keton PASSED                     [ 11%]
tests/test_functionele_groepen.py::test_aldehyde_krijgt_extra_reden PASSED [ 11%]
tests/test_functionele_groepen.py::test_ester_vraagt_sterke_c_o_c_band PASSED [ 12%]
tests/test_functionele_groepen.py::test_carbonzuur_vloeistof_en_gas PASSED [ 12%]
tests/test_functionele_groepen.py::test_nitril PASSED                    [ 13%]
tests/test_functionele_groepen.py::test_primair_amine_twee_nh_pieken_plus_buiging PASSED [ 13%]
tests/test_functionele_groepen.py::test_alkeen_zekerheid_hangt_af_van_steun PASSED [ 14%]
tests/test_functionele_groepen.py::test_aromaat PASSED                   [ 15%]
tests/test_functionele_groepen.py::test_elke_bevinding_noemt_de_piek_als_reden PASSED [ 15%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[aceton_gas -> C=O (keton of aldehyde)] PASSED [ 16%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[ethanol_gas -> O\u2013H (alcohol of fenol)] PASSED [ 16%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[ethanol_oplossing -> O\u2013H (alcohol of fenol)] PASSED [ 17%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[ethylacetaat_gas -> Ester (\u2013COO\u2013)] PASSED [ 17%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[azijnzuur_oplossing -> Carbonzuur (\u2013COOH)] PASSED [ 18%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[benzonitril_vloeistof_micrometer -> C\u2261N (nitril)] PASSED [ 18%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[benzonitril_vloeistof_micrometer -> Aromaat (benzeenring)] PASSED [ 19%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[1-hexeen_gas -> C=C (alkeen)] PASSED [ 19%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[butylamine_vloeistof -> N\u2013H (amine)] PASSED [ 20%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[tolueen_vloeistof -> Aromaat (benzeenring)] PASSED [ 20%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[aceton_gas] PASSED [ 21%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[ethanol_gas] PASSED [ 21%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[1-hexeen_gas] PASSED [ 22%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[tolueen_vloeistof] PASSED [ 22%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[butylamine_vloeistof] PASSED [ 23%]
tests/test_jcamp_lezen.py::test_kop_en_data_van_aceton PASSED            [ 23%]
tests/test_jcamp_lezen.py::test_micrometer_bestand_houdt_eigen_eenheid PASSED [ 24%]
tests/test_jcamp_lezen.py::test_xfactor_en_yfactor_worden_toegepast PASSED [ 24%]
tests/test_jcamp_lezen.py::test_aflopende_x_as PASSED                    [ 25%]
tests/test_jcamp_lezen.py::test_aan_elkaar_geplakte_getallen_met_mintekens PASSED [ 25%]
tests/test_jcamp_lezen.py::test_gecomprimeerde_data_difdup PASSED        [ 26%]
tests/test_jcamp_lezen.py::test_xypoints_en_peak_table PASSED            [ 26%]
tests/test_jcamp_lezen.py::test_meerdere_blokken_neemt_eerste_met_data PASSED [ 27%]
tests/test_jcamp_lezen.py::test_bestand_zonder_data_geeft_jcampfout PASSED [ 27%]
tests/test_jcamp_lezen.py::test_opmerkingen_met_dollartekens_worden_genegeerd PASSED [ 28%]
tests/test_jcamp_lezen.py::test_zelfde_uitkomst_als_bibliotheek_jcamp PASSED [ 29%]
tests/test_matching.py::test_identiek_spectrum_scoort_100[cosinus] PASSED [ 29%]
tests/test_matching.py::test_identiek_spectrum_scoort_100[pearson] PASSED [ 30%]
tests/test_matching.py::test_identiek_spectrum_scoort_100[euclidisch] PASSED [ 30%]
tests/test_matching.py::test_cosinus_en_pearson_negeren_schaal_euclidisch_niet PASSED [ 31%]
tests/test_matching.py::test_pearson_negeert_constante_verschuiving_cosinus_niet PASSED [ 31%]
tests/test_matching.py::test_niet_overlappende_pieken_scoren_laag PASSED [ 32%]
tests/test_matching.py::test_handmatig_nagerekend_voorbeeld PASSED       [ 32%]
tests/test_matching.py::test_alleen_gemeenschappelijk_bereik_telt_mee PASSED [ 33%]
tests/test_matching.py::test_te_weinig_overlap_geeft_score_0 PASSED      [ 33%]
tests/test_matching.py::test_meerdere_vragen_tegelijk_geeft_zelfde_als_los PASSED [ 34%]
tests/test_matching.py::test_onbekende_methode_geeft_duidelijke_fout PASSED [ 34%]
tests/test_matching.py::test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer[cosinus] PASSED [ 35%]
tests/test_matching.py::test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer[pearson] PASSED [ 35%]
tests/test_matching.py::test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer[euclidisch] PASSED [ 36%]
tests/test_matching.py::test_negeer_identiek_laat_het_exacte_spectrum_weg PASSED [ 36%]
tests/test_matching.py::test_waarschuwing_bij_lage_score_en_bij_klein_verschil PASSED [ 37%]
tests/test_matching.py::test_echte_bibliotheek_is_compleet PASSED        [ 37%]
tests/test_matching.py::test_aceton_wordt_herkend_ook_zonder_het_identieke_spectrum PASSED [ 38%]
tests/test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde[cosinus] PASSED [ 38%]
tests/test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde[pearson] PASSED [ 39%]
tests/test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde[euclidisch] PASSED [ 39%]
tests/test_matching.py::test_pieken_uit_selectie PASSED                  [ 40%]
tests/test_piek_toewijzing.py::test_correlatietabel_is_consistent PASSED [ 40%]
tests/test_piek_toewijzing.py::test_bekende_banden[1715-20-C=O: rek, keton] PASSED [ 41%]
tests/test_piek_toewijzing.py::test_bekende_banden[2230-15-C\u2261N] PASSED [ 41%]
tests/test_piek_toewijzing.py::test_bekende_banden[2925-30-C\u2013H: rek, alkaan] PASSED [ 42%]
tests/test_piek_toewijzing.py::test_bekende_banden[3002-40-C\u2013H: rek, alkaan] PASSED [ 43%]
tests/test_piek_toewijzing.py::test_bekende_banden[3080-25-=C\u2013H] PASSED [ 43%]
tests/test_piek_toewijzing.py::test_bekende_banden[3650-40-O\u2013H: vrije rek] PASSED [ 44%]
tests/test_piek_toewijzing.py::test_bekende_banden[3350-250-O\u2013H: rek met waterstofbruggen] PASSED [ 44%]
tests/test_piek_toewijzing.py::test_bekende_banden[1642-30-C=C: rek, alkeen] PASSED [ 45%]
tests/test_piek_toewijzing.py::test_bekende_banden[2349-20-O=C=O] PASSED [ 45%]
tests/test_piek_toewijzing.py::test_breedte_bepaalt_oh_of_nh PASSED      [ 46%]
tests/test_piek_toewijzing.py::test_piek_buiten_alle_gebieden_geeft_eerlijk_antwoord PASSED [ 46%]
tests/test_piek_toewijzing.py::test_vingerafdrukgebied_wordt_vermeld PASSED [ 47%]
tests/test_piek_toewijzing.py::test_tabel_gesorteerd_van_hoog_naar_laag_golfgetal PASSED [ 47%]
tests/test_piek_toewijzing.py::test_regels_worden_aan_de_juiste_piek_gekoppeld PASSED [ 48%]
tests/test_piek_toewijzing.py::test_elke_door_een_regel_genoemde_piek_staat_in_de_tabel PASSED [ 48%]
tests/test_piek_toewijzing.py::test_boventonen_alleen_bij_zwakke_pieken PASSED [ 49%]
tests/test_piekdetectie.py::test_vijf_bekende_pieken_worden_precies_gevonden PASSED [ 49%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[0] PASSED     [ 50%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[1] PASSED     [ 50%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[2] PASSED     [ 51%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[3] PASSED     [ 51%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[4] PASSED     [ 52%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[5] PASSED     [ 52%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[6] PASSED     [ 53%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[7] PASSED     [ 53%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[8] PASSED     [ 54%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[9] PASSED     [ 54%]
tests/test_piekdetectie.py::test_alleen_ruis_geeft_geen_pieken PASSED    [ 55%]
tests/test_piekdetectie.py::test_veel_ruis_piek_onder_de_ruis_wordt_niet_gemeld PASSED [ 55%]
tests/test_piekdetectie.py::test_losse_uitschieter_is_geen_piek PASSED   [ 56%]
tests/test_piekdetectie.py::test_twee_overlappende_pieken_worden_los_gevonden PASSED [ 56%]
tests/test_piekdetectie.py::test_brede_band_wordt_als_breed_herkend PASSED [ 57%]
tests/test_piekdetectie.py::test_ruisschatting_met_mad_klopt_ongeveer PASSED [ 58%]
tests/test_piekdetectie.py::test_gladmaken_behoudt_piekhoogte_en_vermindert_ruis PASSED [ 58%]
tests/test_piekdetectie.py::test_vlak_of_leeg_spectrum_geeft_lege_lijst PASSED [ 59%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[aceton_gas: C=O-rek van aceton] PASSED [ 59%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[aceton_gas_micrometer: C=O-rek van aceton (bestand in micrometer/transmissie)] PASSED [ 60%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethanol_gas: vrije O-H-rek van ethanol in gasfase] PASSED [ 60%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethanol_gas: C-O-rek van ethanol] PASSED [ 61%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethanol_oplossing: brede O-H-rek van ethanol met waterstofbruggen] PASSED [ 61%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethylacetaat_gas: C=O-rek van de ester] PASSED [ 62%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethylacetaat_gas: C-O-C-rek van de ester] PASSED [ 62%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[azijnzuur_oplossing: C=O-rek van het carbonzuur (dimeer)] PASSED [ 63%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[benzonitril_vloeistof_micrometer: C\u2261N-rek van het nitril] PASSED [ 63%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[1-hexeen_gas: C=C-rek van het alkeen] PASSED [ 64%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[1-hexeen_gas: =C-H-rek boven 3000] PASSED [ 64%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[butylamine_vloeistof: N-H-rek van het amine] PASSED [ 65%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[tolueen_vloeistof: C-H-buiging van mono-gesubstitueerde benzeenring] PASSED [ 65%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[tolueen_vloeistof: ringtrilling rond 1500] PASSED [ 66%]
tests/test_piekdetectie.py::test_co_van_aceton_is_de_hoogste_piek PASSED [ 66%]
tests/test_prestatie.py::test_bestand_van_5_mb_binnen_2_seconden PASSED  [ 67%]
tests/test_prestatie.py::test_grafiek_wordt_uitgedund_maar_houdt_de_pieken PASSED [ 67%]
tests/test_prestatie.py::test_te_groot_bestand_wordt_snel_afgewezen PASSED [ 68%]
tests/test_validatie.py::test_geldig_bestand_wordt_geaccepteerd PASSED   [ 68%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.jdx] PASSED [ 69%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.JDX] PASSED [ 69%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.Jdx] PASSED [ 70%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.dx] PASSED [ 70%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.DX] PASSED [ 71%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[mijn spectrum.v2.jdx] PASSED [ 72%]
tests/test_validatie.py::test_alle_voorbeeldspectra_zijn_geldig PASSED   [ 72%]
tests/test_validatie.py::test_windows_regeleindes_en_bom_zijn_geen_probleem PASSED [ 73%]
tests/test_validatie.py::test_kapot_1_leeg_bestand PASSED                [ 73%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.csv] PASSED [ 74%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.txt] PASSED [ 74%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.pdf] PASSED [ 75%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.jdx.exe] PASSED [ 75%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum] PASSED [ 76%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.jdxx] PASSED [ 76%]
tests/test_validatie.py::test_kapot_3_binaire_rommel PASSED              [ 77%]
tests/test_validatie.py::test_kapot_4_ontbrekende_labels PASSED          [ 77%]
tests/test_validatie.py::test_kapot_5_onzin_in_datablok PASSED           [ 78%]
tests/test_validatie.py::test_kapot_6_te_groot_bestand PASSED            [ 78%]
tests/test_validatie.py::test_npoints_klopt_niet PASSED                  [ 79%]
tests/test_validatie.py::test_afgekapt_bestand_wordt_afgekeurd PASSED    [ 79%]
tests/test_validatie.py::test_end_voor_het_datablok PASSED               [ 80%]
tests/test_validatie.py::test_geen_jcamp_maar_gewone_tekst PASSED        [ 80%]
tests/test_validatie.py::test_csv_met_jdx_extensie PASSED                [ 81%]
tests/test_validatie.py::test_vermomd_binair_bestand[PK\x03\x04] PASSED  [ 81%]
tests/test_validatie.py::test_vermomd_binair_bestand[%PDF-1.7\n] PASSED  [ 82%]
tests/test_validatie.py::test_vermomd_binair_bestand[\x89PNG\r\n\x1a\n] PASSED [ 82%]
tests/test_validatie.py::test_vermomd_binair_bestand[MZ\x90\x00] PASSED  [ 83%]
tests/test_validatie.py::test_nulbytes_midden_in_tekst PASSED            [ 83%]
tests/test_validatie.py::test_leeg_datablok PASSED                       [ 84%]
tests/test_validatie.py::test_nan_en_oneindig_in_data PASSED             [ 84%]
tests/test_validatie.py::test_onbekende_eenheden PASSED                  [ 85%]
tests/test_validatie.py::test_te_weinig_punten PASSED                    [ 86%]
tests/test_validatie.py::test_html_en_script_in_titel_is_gewoon_tekst PASSED [ 86%]
tests/test_validatie.py::test_enorm_herhaalgetal_in_gecomprimeerde_data_blaast_geheugen_niet_op PASSED [ 87%]
tests/test_validatie.py::test_willekeurig_beschadigde_bestanden_crashen_nooit PASSED [ 87%]
tests/test_voorbewerking.py::test_raster_is_550_tot_3798_in_stappen_van_4 PASSED [ 88%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[1/CM-golfgetal] PASSED [ 88%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[cm-1-golfgetal] PASSED [ 89%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[1/cm-golfgetal] PASSED [ 89%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[MICROMETERS-micrometer] PASSED [ 90%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[Microns-micrometer] PASSED [ 90%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[NANOMETERS-nanometer] PASSED [ 91%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[HZ-None] PASSED    [ 91%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[TRANSMITTANCE-transmissie] PASSED [ 92%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[% Transmittance-transmissie] PASSED [ 92%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[%T-transmissie] PASSED [ 93%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[ABSORBANCE-absorbantie] PASSED [ 93%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[(micromol/mol)-1m-1 (base 10)-absorptiecoefficient] PASSED [ 94%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[Reflectance-None] PASSED [ 94%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[dispersion index-None] PASSED [ 95%]
tests/test_voorbewerking.py::test_micrometer_naar_golfgetal PASSED       [ 95%]
tests/test_voorbewerking.py::test_transmissie_naar_absorbantie PASSED    [ 96%]
tests/test_voorbewerking.py::test_piek_blijft_op_zijn_plek_na_omzetten_naar_raster PASSED [ 96%]
tests/test_voorbewerking.py::test_masker_geeft_gemeten_bereik_aan PASSED [ 97%]
tests/test_voorbewerking.py::test_hoge_en_lage_resolutie_geven_bijna_hetzelfde_raster PASSED [ 97%]
tests/test_voorbewerking.py::test_normaliseren_zet_basislijn_op_0_en_maximum_op_1 PASSED [ 98%]
tests/test_voorbewerking.py::test_micrometer_en_golfgetal_van_aceton_komen_overeen PASSED [ 98%]
tests/test_voorbewerking.py::test_te_smal_spectrum_wordt_geweigerd PASSED [ 99%]
tests/test_voorbewerking.py::test_vergelijkingsvorm_negeert_basislijn_en_schaal PASSED [100%]

193 passed in 15.12s
```
