# IR-Stofherkenner

Een webapp waarin een laborant een **IR-spectrum (JCAMP-DX)** uploadt. De app:

1. controleert het bestand streng en leest het in;
2. toont direct een grafiek van het spectrum met de gevonden pieken gemarkeerd;
3. vergelijkt het spectrum met ruim 18.000 referentiespectra uit het NIST Chemistry WebBook;
4. toont een **top 5** van meest waarschijnlijke stoffen (naam, CAS-nummer, molecuulformule, overeenkomst 0–100%);
5. legt het beste referentiespectrum over het geüploade spectrum heen;
6. legt uit welke **functionele groepen** waarschijnlijk aanwezig zijn, met de piek als reden
   (bijv. "C=O-rek: piek bij 1742 cm⁻¹").

Project voor de minor AI (Hogeschool Utrecht), opleiding Chemische Technologie.

> ⚠️ **Hulpmiddel, geen bewijs.** De uitkomst is een suggestie op basis van gelijkenis. Gebruik de app nooit als
> enige basis om een onbekende of gevaarlijke stof te identificeren. Zie [docs/ethiek_en_verantwoord_gebruik.md](docs/ethiek_en_verantwoord_gebruik.md).

## Starten (Windows)

Nodig: **Python 3.12 of hoger** (zie "Bekende beperkingen") en internet voor de eerste installatie.

1. **Eenmalig:** dubbelklik op **`setup.bat`**. Dit maakt een virtual environment (`.venv`), installeert de pakketten,
   downloadt de database (± 200 MB) en bouwt de referentiebibliotheek. Duur: ongeveer 5–10 minuten.
2. **Elke keer:** dubbelklik op **`start.bat`**. De app opent in je browser op <http://localhost:8501>.
   Laat het zwarte venster open; sluiten = app stoppen.

Geen eigen spectrum bij de hand? Kies in de app een van de tien voorbeeldspectra.

## Hoe werkt het? (kort)

Er wordt **geen model getraind**. De app gebruikt klassieke (symbolische) AI:

| Onderdeel | Techniek | Bestand |
|---|---|---|
| Inlezen en controleren | eigen JCAMP-DX-parser + strenge validatie | `stofherkenner/jcamp_lezen.py`, `validatie.py` |
| Voorbewerken | cm⁻¹, absorbantie, raster 550–3798 cm⁻¹ (4 cm⁻¹), normaliseren | `stofherkenner/voorbewerking.py` |
| Pieken vinden | Savitzky-Golay, ruis via MAD, prominentie-drempel, minimale breedte | `stofherkenner/piekdetectie.py` |
| Stof zoeken | similarity search: cosinusgelijkenis op logaritme + afgeleide | `stofherkenner/matching.py` |
| Uitleg | expertsysteem met ALS-DAN-regels voor 8 functionele groepen | `stofherkenner/functionele_groepen.py` |
| Scherm | Streamlit + Plotly | `app.py`, `stofherkenner/grafieken.py` |

Meer: [docs/ontwerp.md](docs/ontwerp.md) (architectuur en ontwerpkeuzes).

## Hoe goed is het?

Gemeten met een leave-one-out-evaluatie op 3.934 spectra van 1.735 stoffen (zie [docs/evaluatie.md](docs/evaluatie.md)):
de juiste stof staat in ongeveer **53%** van de gevallen op plek 1 en in ongeveer **70%** in de top 5.
Is er een referentie in dezelfde fase (gas/vloeistof/vast), dan is dat beduidend hoger; is de stof alleen in een
andere fase gemeten, dan beduidend lager. Zoeken door de hele bibliotheek duurt enkele tientallen milliseconden.

## Projectstructuur

```
app.py                     de webapp
stofherkenner/             alle rekenwerk, in kleine modules
scripts/                   database downloaden/bouwen, evaluatie, regeltoets
tests/                     pytest-tests (draaien: .venv\Scripts\python -m pytest)
notebooks/                 notebook piekdetectie en matching (LS)
research/                  onderzoek JCAMP-DX-bibliotheken (RS) + 10 voorbeeldspectra
docs/                      alle documentatie en bewijs voor de leeruitkomsten
data/                      (niet in git) de gedownloade database en de bibliotheek
```

Handige commando's (vanuit de projectmap):

```
.venv\Scripts\python -m pytest                              alle tests
.venv\Scripts\python scripts\evaluatie.py                   evaluatie opnieuw draaien
.venv\Scripts\python -m notebook notebooks\piekdetectie_en_matching.ipynb
```

Gebruik `.venv\Scripts\python -m notebook` en niet alleen `jupyter`: op deze computer wijst `jupyter` naar Anaconda.
Het notebook is al uitgevoerd en bevat alle uitvoer en grafieken, dus je kunt het ook lezen zonder het opnieuw te
draaien. (Opnieuw uitvoeren vanuit Jupyter is in de omgeving van de AI-assistent niet gelukt en daarom niet getest;
`.venv\Scripts\python scripts\voer_notebook_uit.py notebooks\piekdetectie_en_matching.ipynb` werkt wel.)

## Bekende beperkingen

- **Python 3.12+ nodig**, niet 3.10: de vastgezette versies van numpy (2.5) en scipy (1.18) vereisen 3.12. De
  opdracht vroeg 3.10+; zie [docs/criteria_checklist.md](docs/criteria_checklist.md).
- Ongeveer de helft van de referentiespectra is in **gasfase** gemeten; een ATR-, vloeistof- of vaste-stofspectrum
  wijkt daarvan af.
- Alleen stoffen die in de database staan kunnen gevonden worden; **mengsels** worden niet herkend.

## Bronvermelding

- **Referentiespectra:** NIST Chemistry WebBook, NIST Standard Reference Database Number 69, eds. P.J. Linstrom and
  W.G. Mallard, National Institute of Standards and Technology, Gaithersburg MD, <https://webbook.nist.gov/>.
  © U.S. Secretary of Commerce on behalf of the United States of America. Alle rechten voorbehouden.
- **Verzameling:** NistChemData van Ivan Chernyshov (nu <https://github.com/muCommons/NistChemData>). Dit is een
  **onofficiële** verzameling, geen product van NIST. De oorspronkelijke repository heeft de databestanden in mei
  2026 verwijderd; `scripts/download_database.py` haalt het oude archief uit een fork en controleert het met een
  SHA-256-controlegetal. De data is alleen voor lokaal gebruik in onderwijs en zit **niet** in deze repository (op
  tien kleine voorbeeldbestanden na). Zie [docs/ethiek_en_verantwoord_gebruik.md](docs/ethiek_en_verantwoord_gebruik.md).
- **Correlatietabellen** voor de functionele groepen: Pavia e.a., *Introduction to Spectroscopy*; Silverstein e.a.,
  *Spectrometric Identification of Organic Compounds*; Socrates, *Infrared and Raman Characteristic Group Frequencies*.

## Documentatie

| Document | Inhoud |
|---|---|
| [docs/ontwerp.md](docs/ontwerp.md) | Architectuur (Mermaid) en ontwerpkeuzes |
| [docs/onderzoek_jcamp_bibliotheken.md](docs/onderzoek_jcamp_bibliotheken.md) | Onderzoek welke JCAMP-DX-bibliotheek (RS) |
| [docs/theorie_matching.md](docs/theorie_matching.md) | Euclidisch, cosinus, Pearson uitgelegd (LS) |
| [docs/evaluatie.md](docs/evaluatie.md) | Top-1/top-5, fouten, betrouwbaarheid van de score |
| [docs/vergelijking_voorbewerking.md](docs/vergelijking_voorbewerking.md) | Waarom logaritme + afgeleide |
| [docs/controle_functionele_groepen.md](docs/controle_functionele_groepen.md) | Hoe goed de 8 regels werken |
| [docs/testresultaten.md](docs/testresultaten.md) | Uitvoer van alle tests en metingen |
| [docs/criteria_checklist.md](docs/criteria_checklist.md) | Elk criterium: gehaald of niet, met bewijs |
| [docs/demo_script.md](docs/demo_script.md) | Demo van 5 minuten |
| [docs/bewijs_leeruitkomsten.md](docs/bewijs_leeruitkomsten.md) | Bewijs per leeruitkomst |
