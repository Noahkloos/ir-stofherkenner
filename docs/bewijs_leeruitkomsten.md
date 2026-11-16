# Bewijs per leeruitkomst

Overzicht van de bestanden in deze repository die als bewijs dienen. Waar een document door de AI als concept is
opgesteld, staat dat in het document zelf met **[CONCEPT – zelf nalezen en aanvullen]**.
**De zelfevaluatie en reflectie schrijf je zelf**; per leeruitkomst staan hieronder richtvragen.

---

## LU1 – AI-impact op de beroepspraktijk analyseren en evalueren

| Bewijs | Wat laat het zien? |
|---|---|
| [`docs/ai_impact_beroepspraktijk.md`](ai_impact_beroepspraktijk.md) **[CONCEPT]** | Tijdwinst, minder handmatig vergelijken, risico op blind vertrouwen, rol van vakkennis, onderbouwd met meetresultaten |
| [`docs/evaluatie.md`](evaluatie.md) | De meetresultaten zelf: top-1/top-5, per fase, scoreverdelingen, effect van de waarschuwingen |
| [`docs/demo_eerlijke_test.txt`](demo_eerlijke_test.txt) | Concrete voorbeelden van goede en foute uitkomsten |

**Richtvragen voor je zelfevaluatie/reflectie:**
- Wat heb je geleerd over hoe AI het werk van een laborant verandert, dat je vooraf niet verwachtte?
- Welke cijfers uit de evaluatie vond je het meest overtuigend in je analyse, en waarom?
- Heb je de analyse getoetst bij iemand uit de praktijk? Zo niet, hoe zou je dat doen?

## LU2 – Praktijkgerichte AI-oplossing ontwerpen, realiseren en presenteren

| Bewijs | Wat laat het zien? |
|---|---|
| [`docs/ontwerp.md`](ontwerp.md) | Architectuurschema (Mermaid) en onderbouwde ontwerpkeuzes |
| De werkende app: [`app.py`](../app.py) en [`stofherkenner/`](../stofherkenner/) | Realisatie in kleine, onderhoudbare modules met Nederlands commentaar |
| [`README.md`](../README.md), [`setup.bat`](../setup.bat), [`start.bat`](../start.bat) | Installeren en starten met een dubbelklik |
| [`docs/demo_script.md`](demo_script.md) | Demo van 5 minuten, inclusief een voorbeeld waar het systeem fout gaat |
| [`docs/onderzoek_jcamp_bibliotheken.md`](onderzoek_jcamp_bibliotheken.md) + [`research/`](../research/) | Onderzoek vóór een technische keuze (RS) |
| [`notebooks/piekdetectie_en_matching.ipynb`](../notebooks/piekdetectie_en_matching.ipynb), [`docs/theorie_matching.md`](theorie_matching.md) | De theorie achter het ontwerp (LS) |
| [`tests/`](../tests/), [`docs/testresultaten.md`](testresultaten.md), [`docs/criteria_checklist.md`](criteria_checklist.md) | Kwaliteit aantoonbaar gemaakt |

**Richtvragen:**
- Welke ontwerpkeuze zou je nu anders maken, en waarom?
- Kun je de piekdetectie in vier stappen uitleggen zonder het notebook erbij? (oefen dit voor de presentatie)
- Welk criterium is niet (helemaal) gehaald, en hoe verdedig je dat?
- Hoe liep de demo bij het oefenen? Wat pas je aan?

## LU3 – Ethiek en verantwoord AI-gebruik beoordelen

| Bewijs | Wat laat het zien? |
|---|---|
| [`docs/ethiek_en_verantwoord_gebruik.md`](ethiek_en_verantwoord_gebruik.md) **[CONCEPT]** | Beperkingen, risico van te veel vertrouwen, veiligheid, bronvermelding en gebruiksvoorwaarden, transparantie |
| Disclaimer en bronvermelding in de app | Zichtbaar bovenaan en in de zijbalk; getest in `tests/test_app.py::test_app_start_zonder_fouten_en_toont_disclaimer` |
| Waarschuwingen bij lage score / kleine voorsprong | `stofherkenner/matching.py::beoordeel_resultaat`, effect gemeten in `docs/evaluatie.md` |
| Keuze over de herkomst van de data | `docs/ai_logboek.md` stap 2–3 en `docs/ethiek_en_verantwoord_gebruik.md` §4 |

**Richtvragen:**
- Je koos ervoor de data uit een fork te halen nadat de verzamelaar hem had teruggetrokken. Hoe kijk je daar nu op terug?
- Welke ethische afweging vond je het moeilijkst?
- Wat zou er moeten gebeuren voordat deze app in een echt lab gebruikt mag worden?

## LU4 – AI-tools en -technieken gebruiken

| Bewijs | Wat laat het zien? |
|---|---|
| [`docs/ai_logboek.md`](ai_logboek.md) | Stappen van de AI-assistent, problemen en oplossingen, keuzes en wie ze maakte; uitleg van de AI-technieken in de app en waarom geen machine learning |
| De git-geschiedenis (`git log`) | Werk in stappen, met een commit per user story |
| [`stofherkenner/functionele_groepen.py`](../stofherkenner/functionele_groepen.py) | Expertsysteem (symbolische AI) |
| [`stofherkenner/matching.py`](../stofherkenner/matching.py) | Similarity search |

**Richtvragen:**
- Hoe heb je de AI-assistent aangestuurd? Wat werkte goed in je opdrachtomschrijving, wat zou je anders formuleren?
- Hoe heb je gecontroleerd dat de AI geen resultaten verzon?
- Wanneer is symbolische AI een betere keuze dan machine learning, en wanneer niet?

## LU5 – Zelfstandig en zelfsturend werken

| Bewijs | Wat laat het zien? |
|---|---|
| [`docs/planning_en_voortgang.md`](planning_en_voortgang.md) | Dagplanning per user story, wat af is en wat niet, beslissingen onderweg |
| De git-geschiedenis | Een commit per afgeronde story, met tijdstippen |
| [`docs/criteria_checklist.md`](criteria_checklist.md) | Eerlijk overzicht van gehaald / niet gehaald |

**Richtvragen:**
- Hoe heb je je dag ingedeeld, en klopte die planning met hoe het liep?
- Welke beslissing onderweg (bijv. over de database) was het belangrijkst, en hoe nam je die?
- Wat zou je doen met een extra dag?
- Hoe heb je ervoor gezorgd dat je het werk van de AI echt begrijpt en kunt verdedigen?
