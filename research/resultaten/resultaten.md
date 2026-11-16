# Testresultaten JCAMP-DX-bibliotheken

> Automatisch gemaakt door `research/test_jcamp_bibliotheken.py` op 2026-11-16
> met Python 3.14.7. Opnieuw draaien: `.venv\Scripts\python research\test_jcamp_bibliotheken.py`

## 1. De 10 voorbeeldbestanden

"Volledig juist" = data gelezen, x-as geleverd, aantal punten gelijk aan `##NPOINTS`, x-bereik gelijk aan
`##FIRSTX`..`##LASTX` en hoogste y-waarde gelijk aan `##MAXY` (alles vergeleken met de kop van het bestand zelf).

| Bibliotheek | Versie | Importtijd | Zonder fout | Data gelezen | Volledig juist | Titel juist | CAS gevonden | Mediane leestijd (ms) |
|---|---|---|---|---|---|---|---|---|
| eigen parser (stofherkenner.jcamp_lezen) | - | 0.0 s | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 1.15 |
| jcamp | 1.3.2 | 0.03 s | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 4.97 |
| nmrglue (jcampdx) | 0.12 | 1.08 s | 10/10 | 0/10 | 0/10 | 10/10 | 10/10 | 0.4 |
| spectrochempy | 1.3.1 | 0.06 s | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 | 6.95 |
| chemparse | 0.3.2 | 0.0 s | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | - |

Foutmeldingen:
- **chemparse**: `NotImplementedError: chemparse kan geen JCAMP-DX lezen: het is een parser voor chemische formules (functies: ['parse_formula'])`

## 2. Wat gebeurt er met de eenheden?

De voorbeeldbestanden bevatten twee x-eenheden (1/CM en MICROMETERS) en twee y-eenheden (ABSORBANCE en TRANSMITTANCE).
"A → B" betekent: in het bestand staat A, de bibliotheek meldt B.

| Bibliotheek | X-eenheid (bestand → bibliotheek) | X-bereik t.o.v. kop | Y-eenheid (bestand → bibliotheek) | Y-waarden t.o.v. kop |
|---|---|---|---|---|
| eigen parser (stofherkenner.jcamp_lezen) | 1/CM → 1/CM; MICROMETERS → MICROMETERS | klopt | ABSORBANCE → ABSORBANCE; TRANSMITTANCE → TRANSMITTANCE | kloppen |
| jcamp | 1/CM → 1/CM; MICROMETERS → MICROMETERS | klopt | ABSORBANCE → ABSORBANCE; TRANSMITTANCE → TRANSMITTANCE | kloppen |
| nmrglue (jcampdx) | 1/CM → 1/CM; MICROMETERS → MICROMETERS | geen x-as | ABSORBANCE → ABSORBANCE; TRANSMITTANCE → TRANSMITTANCE | geen data |
| spectrochempy | 1/CM → cm⁻¹; MICROMETERS → μm | klopt | ABSORBANCE → a.u.; TRANSMITTANCE → % | kloppen |

Geen enkele kandidaat rekent micrometer om naar cm⁻¹ of transmissie naar absorbantie; dat moet de app dus altijd zelf doen.

## 3. Reactie op kapotte bestanden

| Bibliotheek | leeg bestand | binaire rommel | afgekapt (geen ##END) | onzin in het datablok | kop zonder datablok |
|---|---|---|---|---|---|
| eigen parser (stofherkenner.jcamp_lezen) | fout: JcampFout | fout: JcampFout | GEEN fout, geeft 332 punten terug | fout: JcampFout | fout: JcampFout |
| jcamp | GEEN fout, geeft 0 punten terug | GEEN fout, geeft 0 punten terug | GEEN fout, geeft 332 punten terug | fout: Exception | GEEN fout, geeft 0 punten terug |
| nmrglue (jcampdx) | GEEN fout, geeft 0 punten terug | GEEN fout, geeft 0 punten terug | GEEN fout, geeft 0 punten terug | GEEN fout, geeft 0 punten terug | GEEN fout, geeft 0 punten terug |
| spectrochempy | fout: SpectroChemPyError | fout: SpectroChemPyError | fout: AttributeError | fout: AttributeError | fout: AttributeError |

"GEEN fout" betekent dat de bibliotheek een kapot bestand zonder waarschuwing accepteert; de app zou dan zelf
moeten ontdekken dat er iets mis is.

## 4. Steekproef van 300 bestanden uit de volledige NIST-database

| Bibliotheek | Data gelezen | Volledig juist | Fouten (exceptions) | Totale tijd |
|---|---|---|---|---|
| eigen parser (stofherkenner.jcamp_lezen) | 292/300 | 289/300 | 8 | 0.9 s |
| jcamp | 292/300 | 289/300 | 0 | 2.6 s |
| nmrglue (jcampdx) | 0/300 | 0/300 | 0 | 0.2 s |
| spectrochempy | 274/300 | 271/300 | 26 | 2.1 s |

De steekproef is vast (random seed 2026), dus elke run test dezelfde bestanden. Een deel van de NIST-bestanden
bevat geen meetpunten (alleen een verwijzing naar een gescande afbeelding) of twee blokken; dat verklaart waarom
geen enkele parser 300/300 haalt.

Details per bestand: `research/resultaten/per_bestand.csv`.
