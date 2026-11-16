# Onderzoek: welke Python-bibliotheek voor JCAMP-DX?

**User story (RS):** *"Als ontwikkelaar wil ik onderzoeken hoe we chemische spectra-data kunnen inlezen en parsen met
Python, zodat we weten welke bibliotheek het meest geschikt is om JCAMP-DX-bestanden te verwerken."*

Datum van het onderzoek: 16 november 2026 · Python 3.14.7 · Windows 10

## 1. Samenvatting en advies

| | |
|---|---|
| **Advies** | De app gebruikt een **eigen, kleine parser** (`stofherkenner/jcamp_lezen.py`, ± 250 regels). De bibliotheek **`jcamp`** dient als onafhankelijke controle in de tests. |
| **Waarom** | (1) De eigen parser en `jcamp` lezen de data even goed (10/10 voorbeeldbestanden en 289/300 in de steekproef volledig juist). (2) `jcamp` accepteert kapotte bestanden zonder foutmelding (leeg bestand, binaire rommel), terwijl de user story juist strenge validatie met nette Nederlandse meldingen eist. (3) De eigen parser is ongeveer 4× sneller en heeft geen extra afhankelijkheid. (4) Geen enkele bibliotheek rekent eenheden om; dat moet de app hoe dan ook zelf doen. |
| **Correctie op de sprintplanning** | **`chemparse` kan geen JCAMP-DX lezen.** Het is een parser voor chemische *formules* (PyPI-omschrijving: "Chemical formula parser"; enige functie: `parse_formula("C3H6O")` → `{'C': 3, 'H': 6, 'O': 1}`). Het is daarom als kandidaat afgevallen en vervangen door `spectrochempy`. |

## 2. Onderzochte bibliotheken

| Bibliotheek | Wat is het? | Leest JCAMP-DX? |
|---|---|---|
| [`jcamp`](https://github.com/nzhagen/jcamp) | Klein pakket (één bestand) speciaal voor JCAMP-DX | Ja |
| [`nmrglue`](https://github.com/jjhelmus/nmrglue) (module `jcampdx`) | Pakket voor NMR-data; kan JCAMP-DX van NMR-spectra lezen | Alleen de kop; bij IR-spectra geen data (zie §4) |
| [`spectrochempy`](https://github.com/spectrochempy/spectrochempy) | Groot pakket voor spectroscopie (inlezen, bewerken, analyseren) | Ja (`read_jcamp`) |
| [`chemparse`](https://github.com/gmboyer/chemparse) | Parser voor chemische formules | **Nee** (correctie, zie §1) |
| eigen parser | `stofherkenner/jcamp_lezen.py`, speciaal voor deze app geschreven | Ja |

## 3. Onderhoud en Python-versie

Live opgezocht op 16 november 2026 met `research/onderhoud_bibliotheken.py` (bronnen: PyPI-API en GitHub-API);
volledige uitvoer in [`research/resultaten/onderhoud.md`](../research/resultaten/onderhoud.md).

| Bibliotheek | Nieuwste versie | Laatste release | Laatste commit | Vereiste Python (volgens PyPI) | Werkt met Python 3.10+? | Actief onderhouden? |
|---|---|---|---|---|---|---|
| jcamp | 1.3.2 | 2026-07-15 | 2026-07-15 | ≥ 3.8 | Ja (getest op 3.14) | Ja, in een rustig tempo |
| nmrglue | 0.12 | 2026-08-16 | 2026-10-08 | niet opgegeven | Installeert en draait op 3.14 | Ja |
| spectrochempy | 1.3.1 | 2026-11-14 | 2026-11-16 | ≥ 3.11 | **Niet op 3.10**; wel op 3.11+ (getest op 3.14) | Ja, zeer actief |
| chemparse | 0.3.2 | 2025-03-11 | 2025-03-11 | ≥ 3.6 | Ja (getest op 3.14) | Weinig activiteit (n.v.t., geen JCAMP-lezer) |

"Getest" betekent hier: geïnstalleerd en gedraaid op Python 3.14.7. Andere Python-versies zijn niet zelf getest;
daarvoor is alleen de opgave op PyPI gebruikt.

## 4. Testresultaten

Het testscript [`research/test_jcamp_bibliotheken.py`](../research/test_jcamp_bibliotheken.py) leest met elke kandidaat
dezelfde bestanden. De uitkomst wordt vergeleken met de kop van het bestand zelf (`##NPOINTS`, `##FIRSTX`, `##LASTX`,
`##MAXY`), die het script onafhankelijk van welke parser dan ook uitleest.
Volledige uitvoer: [`research/resultaten/resultaten.md`](../research/resultaten/resultaten.md).

### 4.1 Tien voorbeeldbestanden

| Bibliotheek | Zonder fout | Data gelezen | Volledig juist | Titel | CAS-nummer | Mediane leestijd |
|---|---|---|---|---|---|---|
| eigen parser | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 1,2 ms |
| jcamp | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 5,0 ms |
| nmrglue | 10/10 | **0/10** | 0/10 | 10/10 | 10/10 | 0,4 ms |
| spectrochempy | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 | 7,0 ms |
| chemparse | 0/10 | 0/10 | 0/10 | – | – | – |

- **nmrglue** geeft geen foutmelding, maar levert bij een IR-spectrum geen datapunten: het zet de kop onder een
  aparte sleutel (`_datatype_INFRAREDSPECTRUM`) en geeft `None` terug als data. Het is duidelijk voor NMR bedoeld.
- **spectrochempy** leest de data goed, maar geeft het CAS-nummer niet door via de metadata die het testscript
  uitleest. Voor de top 5 van de app zijn CAS-nummer en molecuulformule nodig.
- De leestijden zijn voor alle kandidaten ruim snel genoeg; snelheid is hier geen doorslaggevend criterium.

### 4.2 Eenheden: micrometer/cm⁻¹ en transmissie/absorbantie

De voorbeeldbestanden bevatten bewust beide x-eenheden (1/CM en MICROMETERS) en beide y-eenheden (ABSORBANCE en
TRANSMITTANCE).

| Bibliotheek | X-as | Y-as |
|---|---|---|
| eigen parser | Laat de eenheid zoals in het bestand; omrekenen gebeurt apart in `voorbewerking.py` | Idem |
| jcamp | Laat de eenheid zoals in het bestand | Laat de eenheid zoals in het bestand |
| nmrglue | Geen x-as | Geen data |
| spectrochempy | Herkent de eenheid en hangt hem aan de data (`cm⁻¹`, `μm`), maar rekent niet om | Herkent `a.u.` en `%`; waarden ongewijzigd |

**Conclusie:** geen enkele kandidaat rekent micrometer om naar cm⁻¹ of transmissie naar absorbantie. Dat doet de app
zelf (`cm⁻¹ = 10 000 / µm` en `A = −log₁₀(T)`), ongeacht de gekozen bibliotheek.

### 4.3 Kapotte bestanden

| Bibliotheek | Leeg bestand | Binaire rommel | Afgekapt (geen `##END`) | Onzin in het datablok | Kop zonder datablok |
|---|---|---|---|---|---|
| eigen parser (alleen de parser) | nette fout | nette fout | leest de 332 punten die er nog zijn | nette fout | nette fout |
| jcamp | **geen fout**, 0 punten | **geen fout**, 0 punten | **geen fout**, 332 punten | fout (kale `Exception`) | **geen fout**, 0 punten |
| nmrglue | geen fout, 0 punten | geen fout, 0 punten | geen fout, 0 punten | geen fout, 0 punten | geen fout, 0 punten |
| spectrochempy | fout | fout | fout (`AttributeError`) | fout (`AttributeError`) | fout (`AttributeError`) |

Dit is het belangrijkste verschil. `jcamp` en `nmrglue` slikken kapotte bestanden zonder iets te melden;
`spectrochempy` geeft technische Engelse foutmeldingen die voor een laborant niets zeggen. In de app zit vóór de
parser nog de validatielaag (`validatie.py`), die ook het afgekapte bestand afkeurt (ontbrekende `##END` en een
aantal punten dat niet klopt met `##NPOINTS`). Dat is getest in `tests/test_validatie.py`.

### 4.4 Steekproef van 300 bestanden uit de volledige database

Vaste steekproef (random seed 2026) uit de 19.582 NIST-bestanden.

| Bibliotheek | Data gelezen | Volledig juist | Foutmeldingen | Totale tijd |
|---|---|---|---|---|
| eigen parser | 292/300 | 289/300 | 8 (bewust: bestanden zonder meetpunten) | 0,9 s |
| jcamp | 292/300 | 289/300 | 0 (geeft bij die 8 bestanden stil 0 punten terug) | 2,6 s |
| nmrglue | 0/300 | 0/300 | 0 | 0,2 s |
| spectrochempy | 274/300 | 271/300 | 26 | 2,1 s |

De eigen parser en `jcamp` lezen precies evenveel bestanden goed. Dat geen van beide 300/300 haalt komt door de
data: een deel van de NIST-bestanden bevat geen meetpunten (alleen een verwijzing naar een gescande afbeelding).

## 5. Afweging

| Criterium | eigen parser | jcamp | nmrglue | spectrochempy |
|---|---|---|---|---|
| Leest NIST-IR-bestanden juist | ✅ | ✅ | ❌ | ✅ (minder vaak) |
| Naam, CAS en formule beschikbaar | ✅ | ✅ | ✅ | ⚠️ CAS niet |
| Nette foutafhandeling bij kapotte bestanden | ✅ eigen Nederlandse fouten | ❌ slikt ze | ❌ slikt ze | ⚠️ technische fouten |
| Extra afhankelijkheid | geen | klein (1 bestand) | middel | groot (veel pakketten) |
| Onderhoud | zelf (± 250 regels, 11 tests) | actief | actief | zeer actief |
| Gecomprimeerde JCAMP-vormen (DIFDUP) | ✅ (getest met een eigen voorbeeld) | ✅ | n.v.t. | ✅ |
| Werkt met Python 3.10 | n.v.t. (zelfde eis als numpy) | ✅ | waarschijnlijk | ❌ (≥ 3.11) |

**Nadeel van de eigen parser, eerlijk benoemd:** hij is alleen getest op NIST-bestanden en een paar zelfgemaakte
gevallen. Exports van echte spectrometers (Bruker, PerkinElmer, Thermo, Shimadzu) kunnen varianten bevatten die
hier niet voorkomen. Daarom draait in de tests een vergelijking met `jcamp` mee
(`tests/test_jcamp_lezen.py::test_zelfde_uitkomst_als_bibliotheek_jcamp`): geven beide parsers dezelfde punten, dan
is de kans op een leesfout klein. Blijkt de eigen parser in de praktijk een bestandssoort niet aan te kunnen, dan
is terugvallen op `jcamp` (met de eigen validatie ervoor) een logische vervolgstap.

## 6. Zelf herhalen

Vanuit de projectmap, na `setup.bat`:

```
.venv\Scripts\python -m pip install -r research\requirements.txt
.venv\Scripts\python research\test_jcamp_bibliotheken.py
.venv\Scripts\python research\onderhoud_bibliotheken.py
```

De eerste regel installeert eenmalig de onderzoekspakketten; de tweede is het ene commando dat de hele vergelijking
draait. De voorbeeldbestanden staan in [`research/voorbeeldspectra/`](../research/voorbeeldspectra/) (zie de README
daar). Onderdeel 4.4 wordt overgeslagen als de volledige database niet is gedownload.
