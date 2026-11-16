# Onderzoek JCAMP-DX-bibliotheken (RS)

Het verslag staat in [`docs/onderzoek_jcamp_bibliotheken.md`](../docs/onderzoek_jcamp_bibliotheken.md).
Deze map bevat de code en de ruwe resultaten.

## In één commando herhalen

Vanuit de projectmap (na `setup.bat`):

```
.venv\Scripts\python -m pip install -r research\requirements.txt
.venv\Scripts\python research\test_jcamp_bibliotheken.py
```

De eerste regel is een eenmalige installatie van de vier onderzochte pakketten. De tweede regel draait de hele
vergelijking (enkele seconden) en schrijft de resultaten naar `research/resultaten/`.

Onderhoudsgegevens (laatste release en commit) opnieuw opzoeken, internet nodig:

```
.venv\Scripts\python research\onderhoud_bibliotheken.py
```

## Inhoud

| Bestand / map | Wat |
|---|---|
| `test_jcamp_bibliotheken.py` | Leest dezelfde bestanden met elke bibliotheek en vergelijkt de uitkomst met de kop van het bestand |
| `onderhoud_bibliotheken.py` | Zoekt versie, releasedatum, laatste commit en vereiste Python-versie op (PyPI + GitHub) |
| `requirements.txt` | De onderzochte pakketten met vastgezette versies |
| `voorbeeldspectra/` | 10 voorbeeldbestanden uit de NIST-data |
| `resultaten/resultaten.md` | Uitvoer van de vergelijking (automatisch gemaakt) |
| `resultaten/per_bestand.csv` | Uitkomst per bibliotheek en per bestand |
| `resultaten/onderhoud.md` | Uitvoer van het onderhoudsonderzoek |
| `resultaten/kapotte_bestanden/` | De vijf kapotte testbestanden die het script zelf aanmaakt |

## De voorbeeldspectra

Tien bestanden uit het NIST Chemistry WebBook (via NistChemData), gekozen zodat alle varianten voorkomen:

| Bestand | Stof | Fase | X-as | Y-as |
|---|---|---|---|---|
| `aceton_gas_C67641_IR_0.jdx` | aceton | gas | 1/CM | absorbantie |
| `aceton_gas_micrometer_C67641_IR_1.jdx` | aceton | gas | micrometer | transmissie |
| `ethanol_gas_C64175_IR_0.jdx` | ethanol | gas | 1/CM | absorbantie |
| `ethanol_oplossing_C64175_IR_3.jdx` | ethanol | oplossing | 1/CM | transmissie |
| `ethylacetaat_gas_C141786_IR_0.jdx` | ethylacetaat | gas | 1/CM | absorbantie |
| `azijnzuur_oplossing_C64197_IR_2.jdx` | azijnzuur | oplossing | 1/CM | transmissie |
| `benzonitril_vloeistof_micrometer_C100470_IR_1.jdx` | benzonitril | vloeistof | micrometer | transmissie |
| `1-hexeen_gas_C592416_IR_0.jdx` | 1-hexeen | gas | 1/CM | absorbantie |
| `butylamine_vloeistof_C109739_IR_2.jdx` | n-butylamine | vloeistof | 1/CM | transmissie |
| `tolueen_vloeistof_C108883_IR_2.jdx` | tolueen | vloeistof | 1/CM | transmissie |

De bestandsnaam eindigt op de oorspronkelijke NIST-naam (`{NIST Compound ID}_IR_{index}`); het stuk ervoor is
toegevoegd voor de leesbaarheid. De inhoud is ongewijzigd.

**Bron en rechten:** NIST Chemistry WebBook, NIST Standard Reference Database 69 (© U.S. Secretary of Commerce on
behalf of the United States of America), verzameld via de onofficiële repository NistChemData. De bestanden zijn hier
alleen opgenomen als klein voorbeeld voor onderwijs en om de tests te kunnen draaien. Zie ook
[`docs/ethiek_en_verantwoord_gebruik.md`](../docs/ethiek_en_verantwoord_gebruik.md).
