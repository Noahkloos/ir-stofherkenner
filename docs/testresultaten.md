# Testresultaten

Alle uitvoer hieronder komt uit echte runs op 16 november 2026 (Windows 10, Python 3.14.7).
Opnieuw draaien: `.venv\Scripts\python -m pytest -v` (met `-s` erbij zie je ook de `[meting]`-regels).

## 1. Pytest: alle tests

**Resultaat: 171 passed in 12.90s.**

| Testbestand | Aantal | Geslaagd | Wat wordt getest |
|---|---|---|---|
| `test_app.py` | 12 | 12 | De app zelf (Streamlit AppTest): disclaimer, grafiek, top 5, overlay, uploads, eerlijke test, zonder bibliotheek, 5 MB |
| `test_functionele_groepen.py` | 29 | 29 | Expertsysteem: elke regel los en op echte spectra; geen stellige valse meldingen |
| `test_jcamp_lezen.py` | 11 | 11 | Parser: kop, factoren, micrometer, gecomprimeerde data, meerdere blokken; vergelijking met jcamp |
| `test_matching.py` | 21 | 21 | Cosinus/Pearson/Euclidisch, maskers, zoeken, waarschuwingen, snelheid in de echte bibliotheek |
| `test_piekdetectie.py` | 34 | 34 | Synthetische spectra (bekende pieken ±8 cm⁻¹, ruis, spike, overlap) en 14 bekende pieken in echte spectra |
| `test_prestatie.py` | 3 | 3 | Bestand van ~5 MB binnen 2 s; uitdunnen grafiek; te groot bestand snel afgewezen |
| `test_validatie.py` | 37 | 37 | De zes verplichte kapotte bestanden, nog een reeks andere kapotte bestanden, en 400 willekeurig beschadigde bestanden |
| `test_voorbewerking.py` | 24 | 24 | Eenheden, omrekenen µm→cm⁻¹ en T→A, raster, resolutie, normaliseren, vergelijkingsvorm |

## 2. Metingen (uitvoer van `pytest -s`)

```
[meting] app-run met upload van 4.84 MB tot en met grafiek + top 5: 0.42 s
[meting] zoeken (cosinus) door 18016 spectra: 20 ms
[meting] zoeken (pearson) door 18016 spectra: 29 ms
[meting] zoeken (euclidisch) door 18016 spectra: 20 ms
[meting] bestand van 4.84 MB, 565000 meetpunten: valideren + inlezen + analyseren + grafiek in 0.36 s (snelste) / 0.38 s (langzaamste van 3)
```

- **Eis US-K1 (≤ 2 s tot de grafiek bij 5 MB):** gehaald. Het gegenereerde testbestand is 4,84 MB (565.000 meetpunten).
  Gemeten is al het werk van de server: valideren, inlezen, voorbewerken, pieken zoeken, functionele groepen en de
  Plotly-grafiek opbouwen (`test_prestatie.py`), en bij de app-run ook het zoeken in de bibliotheek en de top 5
  (`test_app.py`). Niet gemeten: het tekenen in de browser. De grafiek wordt daarvoor uitgedund tot maximaal
  4.000 punten; in de browser toonde de app bij het ethanolvoorbeeld een verwerkingstijd van 229 ms.
- **Eis matching (< 1 s door de hele bibliotheek):** gehaald, zie de zoektijden hierboven (18.016 spectra).

## 3. Responsiviteit (desktop en tablet)

Gecontroleerd in de ingebouwde browser van de AI-tool (Chromium) met het ethanolvoorbeeld, top 5 en overlay zichtbaar:

| Scherm (geëmuleerd) | Horizontaal scrollen? | Breedte grafiek 1 / grafiek 2 / tabel | Binnen het scherm? | Fouten in de console |
|---|---|---|---|---|
| Desktop 1366 × 900 | nee | 896 / 896 px / – | ja | geen |
| Tablet 768 × 1024 | nee | 726 / 726 / 726 px | ja | geen |

Gemeten met JavaScript in de pagina (`document.documentElement.scrollWidth` tegenover `window.innerWidth`, en de
afmetingen van de Plotly-grafieken en de tabel). Op tabletformaat klapt de zijbalk in en vullen de grafieken de
breedte. **Beperking:** geëmuleerd scherm, geen fysieke tablet; aanraakbediening (zoomen in de grafiek) niet getest.

## 4. setup.bat en start.bat op een schone kopie

De repository is gekloond naar een lege map (met een spatie in het pad: `...\schone test\ir-stofherkenner`), zonder
`.venv` en zonder `data/`. Daarna:

| Stap | Resultaat |
|---|---|
| `setup.bat` | **Exitcode 0 na 364 s.** Venv aangemaakt, pakketten geïnstalleerd, `nist_IR.zip` gedownload en SHA-256 gecontroleerd, 19.582 bestanden uitgepakt, bibliotheek gebouwd: 18.998 spectra, 982 duplicaten, 584 overgeslagen (identiek aan het hoofdproject) |
| Tests in de schone kopie | **169 passed, 1 skipped.** De overgeslagen test vergelijkt met de bibliotheek `jcamp`, die alleen voor het onderzoek nodig is (`research/requirements.txt`) |
| App starten | De app van de schone kopie start en antwoordt binnen 2 s (`/_stcore/health` = ok), zonder vraag om een e-mailadres (headless) |

**Kanttekeningen:**
- Dit is een schone *kopie* op dezelfde computer, geen schone *computer*: Python 3.14 was al geïnstalleerd en er
  kunnen pakketten in de pip-cache hebben gestaan.
- `start.bat` zelf kon niet volledig getest worden: poort 8501 was bezet door een eerder gestarte testserver die
  de AI niet mocht stoppen. Daarom is het startcommando uit `start.bat` op poort 8502 gedraaid. De controles bovenin
  `start.bat` (venv en bibliotheek aanwezig) en het openen van de browser zijn niet automatisch getest.
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
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[spectrum.csv-golfgetal;absorbantie\n4000;0.1\n-accepteert alleen JCAMP-DX-bestanden] PASSED [  2%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[leeg.jdx--leeg] PASSED [  3%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[rommel.jdx-inhoud2-binaire gegevens] PASSED [  4%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[half.jdx-inhoud3-mist verplichte onderdelen] PASSED [  4%]
tests/test_app.py::test_ongeldige_upload_geeft_nederlandse_melding_en_geen_crash[groot.jdx-inhoud4-maximale grootte is 5 MB] PASSED [  5%]
tests/test_app.py::test_geldige_upload_toont_direct_de_grafiek PASSED    [  5%]
tests/test_app.py::test_upload_van_5_mb_in_de_app_binnen_2_seconden PASSED [  6%]
tests/test_app.py::test_app_werkt_ook_zonder_bibliotheek PASSED          [  7%]
tests/test_functionele_groepen.py::test_er_zijn_acht_regels PASSED       [  7%]
tests/test_functionele_groepen.py::test_geen_pieken_geen_bevindingen PASSED [  8%]
tests/test_functionele_groepen.py::test_alcohol_vloeistof_brede_band PASSED [  8%]
tests/test_functionele_groepen.py::test_alcohol_gasfase_smalle_vrije_oh PASSED [  9%]
tests/test_functionele_groepen.py::test_smalle_piek_bij_3400_is_geen_alcohol PASSED [  9%]
tests/test_functionele_groepen.py::test_keton PASSED                     [ 10%]
tests/test_functionele_groepen.py::test_aldehyde_krijgt_extra_reden PASSED [ 11%]
tests/test_functionele_groepen.py::test_ester_vraagt_sterke_c_o_c_band PASSED [ 11%]
tests/test_functionele_groepen.py::test_carbonzuur_vloeistof_en_gas PASSED [ 12%]
tests/test_functionele_groepen.py::test_nitril PASSED                    [ 12%]
tests/test_functionele_groepen.py::test_primair_amine_twee_nh_pieken_plus_buiging PASSED [ 13%]
tests/test_functionele_groepen.py::test_alkeen_zekerheid_hangt_af_van_steun PASSED [ 14%]
tests/test_functionele_groepen.py::test_aromaat PASSED                   [ 14%]
tests/test_functionele_groepen.py::test_elke_bevinding_noemt_de_piek_als_reden PASSED [ 15%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[aceton_gas -> C=O (keton of aldehyde)] PASSED [ 15%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[ethanol_gas -> O\u2013H (alcohol of fenol)] PASSED [ 16%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[ethanol_oplossing -> O\u2013H (alcohol of fenol)] PASSED [ 16%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[ethylacetaat_gas -> Ester (\u2013COO\u2013)] PASSED [ 17%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[azijnzuur_oplossing -> Carbonzuur (\u2013COOH)] PASSED [ 18%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[benzonitril_vloeistof_micrometer -> C\u2261N (nitril)] PASSED [ 18%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[benzonitril_vloeistof_micrometer -> Aromaat (benzeenring)] PASSED [ 19%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[1-hexeen_gas -> C=C (alkeen)] PASSED [ 19%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[butylamine_vloeistof -> N\u2013H (amine)] PASSED [ 20%]
tests/test_functionele_groepen.py::test_verwachte_groep_in_echt_spectrum[tolueen_vloeistof -> Aromaat (benzeenring)] PASSED [ 21%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[aceton_gas] PASSED [ 21%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[ethanol_gas] PASSED [ 22%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[1-hexeen_gas] PASSED [ 22%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[tolueen_vloeistof] PASSED [ 23%]
tests/test_functionele_groepen.py::test_geen_stellige_valse_meldingen[butylamine_vloeistof] PASSED [ 23%]
tests/test_jcamp_lezen.py::test_kop_en_data_van_aceton PASSED            [ 24%]
tests/test_jcamp_lezen.py::test_micrometer_bestand_houdt_eigen_eenheid PASSED [ 25%]
tests/test_jcamp_lezen.py::test_xfactor_en_yfactor_worden_toegepast PASSED [ 25%]
tests/test_jcamp_lezen.py::test_aflopende_x_as PASSED                    [ 26%]
tests/test_jcamp_lezen.py::test_aan_elkaar_geplakte_getallen_met_mintekens PASSED [ 26%]
tests/test_jcamp_lezen.py::test_gecomprimeerde_data_difdup PASSED        [ 27%]
tests/test_jcamp_lezen.py::test_xypoints_en_peak_table PASSED            [ 28%]
tests/test_jcamp_lezen.py::test_meerdere_blokken_neemt_eerste_met_data PASSED [ 28%]
tests/test_jcamp_lezen.py::test_bestand_zonder_data_geeft_jcampfout PASSED [ 29%]
tests/test_jcamp_lezen.py::test_opmerkingen_met_dollartekens_worden_genegeerd PASSED [ 29%]
tests/test_jcamp_lezen.py::test_zelfde_uitkomst_als_bibliotheek_jcamp PASSED [ 30%]
tests/test_matching.py::test_identiek_spectrum_scoort_100[cosinus] PASSED [ 30%]
tests/test_matching.py::test_identiek_spectrum_scoort_100[pearson] PASSED [ 31%]
tests/test_matching.py::test_identiek_spectrum_scoort_100[euclidisch] PASSED [ 32%]
tests/test_matching.py::test_cosinus_en_pearson_negeren_schaal_euclidisch_niet PASSED [ 32%]
tests/test_matching.py::test_pearson_negeert_constante_verschuiving_cosinus_niet PASSED [ 33%]
tests/test_matching.py::test_niet_overlappende_pieken_scoren_laag PASSED [ 33%]
tests/test_matching.py::test_handmatig_nagerekend_voorbeeld PASSED       [ 34%]
tests/test_matching.py::test_alleen_gemeenschappelijk_bereik_telt_mee PASSED [ 35%]
tests/test_matching.py::test_te_weinig_overlap_geeft_score_0 PASSED      [ 35%]
tests/test_matching.py::test_meerdere_vragen_tegelijk_geeft_zelfde_als_los PASSED [ 36%]
tests/test_matching.py::test_onbekende_methode_geeft_duidelijke_fout PASSED [ 36%]
tests/test_matching.py::test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer[cosinus] PASSED [ 37%]
tests/test_matching.py::test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer[pearson] PASSED [ 38%]
tests/test_matching.py::test_zoek_vindt_juiste_stof_en_telt_elke_stof_een_keer[euclidisch] PASSED [ 38%]
tests/test_matching.py::test_negeer_identiek_laat_het_exacte_spectrum_weg PASSED [ 39%]
tests/test_matching.py::test_waarschuwing_bij_lage_score_en_bij_klein_verschil PASSED [ 39%]
tests/test_matching.py::test_echte_bibliotheek_is_compleet PASSED        [ 40%]
tests/test_matching.py::test_aceton_wordt_herkend_ook_zonder_het_identieke_spectrum PASSED [ 40%]
tests/test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde[cosinus] PASSED [ 41%]
tests/test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde[pearson] PASSED [ 42%]
tests/test_matching.py::test_zoeken_in_hele_bibliotheek_duurt_korter_dan_1_seconde[euclidisch] PASSED [ 42%]
tests/test_piekdetectie.py::test_vijf_bekende_pieken_worden_precies_gevonden PASSED [ 43%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[0] PASSED     [ 43%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[1] PASSED     [ 44%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[2] PASSED     [ 45%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[3] PASSED     [ 45%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[4] PASSED     [ 46%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[5] PASSED     [ 46%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[6] PASSED     [ 47%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[7] PASSED     [ 47%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[8] PASSED     [ 48%]
tests/test_piekdetectie.py::test_willekeurige_piekposities[9] PASSED     [ 49%]
tests/test_piekdetectie.py::test_alleen_ruis_geeft_geen_pieken PASSED    [ 49%]
tests/test_piekdetectie.py::test_veel_ruis_piek_onder_de_ruis_wordt_niet_gemeld PASSED [ 50%]
tests/test_piekdetectie.py::test_losse_uitschieter_is_geen_piek PASSED   [ 50%]
tests/test_piekdetectie.py::test_twee_overlappende_pieken_worden_los_gevonden PASSED [ 51%]
tests/test_piekdetectie.py::test_brede_band_wordt_als_breed_herkend PASSED [ 52%]
tests/test_piekdetectie.py::test_ruisschatting_met_mad_klopt_ongeveer PASSED [ 52%]
tests/test_piekdetectie.py::test_gladmaken_behoudt_piekhoogte_en_vermindert_ruis PASSED [ 53%]
tests/test_piekdetectie.py::test_vlak_of_leeg_spectrum_geeft_lege_lijst PASSED [ 53%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[aceton_gas: C=O-rek van aceton] PASSED [ 54%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[aceton_gas_micrometer: C=O-rek van aceton (bestand in micrometer/transmissie)] PASSED [ 54%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethanol_gas: vrije O-H-rek van ethanol in gasfase] PASSED [ 55%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethanol_gas: C-O-rek van ethanol] PASSED [ 56%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethanol_oplossing: brede O-H-rek van ethanol met waterstofbruggen] PASSED [ 56%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethylacetaat_gas: C=O-rek van de ester] PASSED [ 57%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[ethylacetaat_gas: C-O-C-rek van de ester] PASSED [ 57%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[azijnzuur_oplossing: C=O-rek van het carbonzuur (dimeer)] PASSED [ 58%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[benzonitril_vloeistof_micrometer: C\u2261N-rek van het nitril] PASSED [ 59%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[1-hexeen_gas: C=C-rek van het alkeen] PASSED [ 59%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[1-hexeen_gas: =C-H-rek boven 3000] PASSED [ 60%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[butylamine_vloeistof: N-H-rek van het amine] PASSED [ 60%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[tolueen_vloeistof: C-H-buiging van mono-gesubstitueerde benzeenring] PASSED [ 61%]
tests/test_piekdetectie.py::test_bekende_piek_in_echt_spectrum[tolueen_vloeistof: ringtrilling rond 1500] PASSED [ 61%]
tests/test_piekdetectie.py::test_co_van_aceton_is_de_hoogste_piek PASSED [ 62%]
tests/test_prestatie.py::test_bestand_van_5_mb_binnen_2_seconden PASSED  [ 63%]
tests/test_prestatie.py::test_grafiek_wordt_uitgedund_maar_houdt_de_pieken PASSED [ 63%]
tests/test_prestatie.py::test_te_groot_bestand_wordt_snel_afgewezen PASSED [ 64%]
tests/test_validatie.py::test_geldig_bestand_wordt_geaccepteerd PASSED   [ 64%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.jdx] PASSED [ 65%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.JDX] PASSED [ 66%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.Jdx] PASSED [ 66%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.dx] PASSED [ 67%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[a.DX] PASSED [ 67%]
tests/test_validatie.py::test_extensie_is_hoofdletterongevoelig[mijn spectrum.v2.jdx] PASSED [ 68%]
tests/test_validatie.py::test_alle_voorbeeldspectra_zijn_geldig PASSED   [ 69%]
tests/test_validatie.py::test_windows_regeleindes_en_bom_zijn_geen_probleem PASSED [ 69%]
tests/test_validatie.py::test_kapot_1_leeg_bestand PASSED                [ 70%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.csv] PASSED [ 70%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.txt] PASSED [ 71%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.pdf] PASSED [ 71%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.jdx.exe] PASSED [ 72%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum] PASSED [ 73%]
tests/test_validatie.py::test_kapot_2_verkeerde_extensie[spectrum.jdxx] PASSED [ 73%]
tests/test_validatie.py::test_kapot_3_binaire_rommel PASSED              [ 74%]
tests/test_validatie.py::test_kapot_4_ontbrekende_labels PASSED          [ 74%]
tests/test_validatie.py::test_kapot_5_onzin_in_datablok PASSED           [ 75%]
tests/test_validatie.py::test_kapot_6_te_groot_bestand PASSED            [ 76%]
tests/test_validatie.py::test_npoints_klopt_niet PASSED                  [ 76%]
tests/test_validatie.py::test_afgekapt_bestand_wordt_afgekeurd PASSED    [ 77%]
tests/test_validatie.py::test_end_voor_het_datablok PASSED               [ 77%]
tests/test_validatie.py::test_geen_jcamp_maar_gewone_tekst PASSED        [ 78%]
tests/test_validatie.py::test_csv_met_jdx_extensie PASSED                [ 78%]
tests/test_validatie.py::test_vermomd_binair_bestand[PK\x03\x04] PASSED  [ 79%]
tests/test_validatie.py::test_vermomd_binair_bestand[%PDF-1.7\n] PASSED  [ 80%]
tests/test_validatie.py::test_vermomd_binair_bestand[\x89PNG\r\n\x1a\n] PASSED [ 80%]
tests/test_validatie.py::test_vermomd_binair_bestand[MZ\x90\x00] PASSED  [ 81%]
tests/test_validatie.py::test_nulbytes_midden_in_tekst PASSED            [ 81%]
tests/test_validatie.py::test_leeg_datablok PASSED                       [ 82%]
tests/test_validatie.py::test_nan_en_oneindig_in_data PASSED             [ 83%]
tests/test_validatie.py::test_onbekende_eenheden PASSED                  [ 83%]
tests/test_validatie.py::test_te_weinig_punten PASSED                    [ 84%]
tests/test_validatie.py::test_html_en_script_in_titel_is_gewoon_tekst PASSED [ 84%]
tests/test_validatie.py::test_enorm_herhaalgetal_in_gecomprimeerde_data_blaast_geheugen_niet_op PASSED [ 85%]
tests/test_validatie.py::test_willekeurig_beschadigde_bestanden_crashen_nooit PASSED [ 85%]
tests/test_voorbewerking.py::test_raster_is_550_tot_3798_in_stappen_van_4 PASSED [ 86%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[1/CM-golfgetal] PASSED [ 87%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[cm-1-golfgetal] PASSED [ 87%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[1/cm-golfgetal] PASSED [ 88%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[MICROMETERS-micrometer] PASSED [ 88%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[Microns-micrometer] PASSED [ 89%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[NANOMETERS-nanometer] PASSED [ 90%]
tests/test_voorbewerking.py::test_x_eenheid_herkennen[HZ-None] PASSED    [ 90%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[TRANSMITTANCE-transmissie] PASSED [ 91%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[% Transmittance-transmissie] PASSED [ 91%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[%T-transmissie] PASSED [ 92%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[ABSORBANCE-absorbantie] PASSED [ 92%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[(micromol/mol)-1m-1 (base 10)-absorptiecoefficient] PASSED [ 93%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[Reflectance-None] PASSED [ 94%]
tests/test_voorbewerking.py::test_y_eenheid_herkennen[dispersion index-None] PASSED [ 94%]
tests/test_voorbewerking.py::test_micrometer_naar_golfgetal PASSED       [ 95%]
tests/test_voorbewerking.py::test_transmissie_naar_absorbantie PASSED    [ 95%]
tests/test_voorbewerking.py::test_piek_blijft_op_zijn_plek_na_omzetten_naar_raster PASSED [ 96%]
tests/test_voorbewerking.py::test_masker_geeft_gemeten_bereik_aan PASSED [ 97%]
tests/test_voorbewerking.py::test_hoge_en_lage_resolutie_geven_bijna_hetzelfde_raster PASSED [ 97%]
tests/test_voorbewerking.py::test_normaliseren_zet_basislijn_op_0_en_maximum_op_1 PASSED [ 98%]
tests/test_voorbewerking.py::test_micrometer_en_golfgetal_van_aceton_komen_overeen PASSED [ 98%]
tests/test_voorbewerking.py::test_te_smal_spectrum_wordt_geweigerd PASSED [ 99%]
tests/test_voorbewerking.py::test_vergelijkingsvorm_negeert_basislijn_en_schaal PASSED [100%]

171 passed in 12.90s
```
