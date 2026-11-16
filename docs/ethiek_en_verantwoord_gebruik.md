# Ethiek en verantwoord gebruik

Hoort bij **LU3** (ethiek en verantwoord AI-gebruik beoordelen). Alle cijfers komen uit
[`evaluatie.md`](evaluatie.md), [`controle_functionele_groepen.md`](controle_functionele_groepen.md) en
[`demo_eerlijke_test.txt`](demo_eerlijke_test.txt).

> **[CONCEPT – zelf nalezen en aanvullen]** Dit document is door de AI-assistent opgesteld op basis van de
> meetresultaten. Lees het kritisch na, vul aan met je eigen oordeel en pas de formulering aan naar je eigen woorden.

## 1. Beperkingen van het systeem

| Beperking | Wat betekent dit in de praktijk? | Bewijs |
|---|---|---|
| **Gasfase-bias** | 10.060 van de 18.998 spectra in de bibliotheek (53%) zijn in gasfase gemeten. Een spectrum van een vloeistof, vaste stof of ATR-meting wijkt daarvan af: andere piekposities (C=O 15–30 cm⁻¹ lager in vloeistof), geen vrije O–H maar een brede waterstofbrugband. In de evaluatie staat de juiste stof op plek 1 in 85% van de gevallen als er een referentie in dezelfde fase bestaat, maar in 41% als de stof alleen in een andere fase is gemeten. | `docs/evaluatie.md`, `data/build_log.txt` |
| **Alleen stoffen die in de database staan** | Een stof die niet in de bibliotheek zit, wordt nooit gevonden. De app geeft dan toch een "beste" match, vaak een verwante stof. Gesimuleerd: zit de juiste stof er niet in, dan is de beste score nog steeds in de helft van de gevallen hoger dan 69,7%. | `docs/evaluatie.md` (scoreverdelingen) |
| **Geen mengsels** | Een spectrum van een mengsel (of een vervuild monster, of een oplossing waarvan het oplosmiddel meegemeten is) lijkt op geen enkel zuiver referentiespectrum goed. | ontwerp: `docs/ontwerp.md` §4 |
| **Lijkende stoffen** | Isomeren en stoffen uit een homologe reeks (bijv. 1-penteen en 1-hexeen) hebben bijna hetzelfde spectrum. IR alleen kan ze vaak niet onderscheiden. | `docs/evaluatie.md` (foutanalyse), demo: 1-hexeen |
| **Regels voor functionele groepen zijn niet foutloos** | Afhankelijk van de groep vindt een regel 45–80% van de gevallen waarin de groep er (volgens de naam) zit, en gaan sommige regels in 7–9% van de gevallen af waar de groep onmogelijk aanwezig kan zijn. | `docs/controle_functionele_groepen.md` |
| **Getest op NIST-data, niet op eigen metingen** | De evaluatie gebruikt NIST-spectra als "onbekend monster". Een eigen meting (ander apparaat, ATR, waterdamp, CO₂) zal gemiddeld slechter scoren. | `docs/evaluatie.md` §Beperkingen |

## 2. Het risico van te veel vertrouwen in een score

Een getal als "92,6%" ziet er heel zeker uit. De metingen laten zien dat dat misleidend kan zijn:

- Als de app de **verkeerde** stof op plek 1 zet, is de mediane score daarvan **80,6%**. Dat is bijna even hoog als
  wanneer hij het **goed** heeft (mediaan **82,0%**). De score alleen zegt dus weinig over goed of fout.
- De waarschuwingen ("lage score", "nummers 1 en 2 dicht bij elkaar") gaan af bij **78%** van de foute antwoorden.
  Bij ruim **1 op de 5 foute antwoorden** komt er dus géén waarschuwing.
- Concreet voorbeeld uit de demo: **butylamine** wordt herkend als *1,5-pentaandiamine* (80,5%), zonder
  waarschuwing. De juiste stof staat niet eens in de top 5.

Wat de app doet om blind vertrouwen tegen te gaan:

1. De score heet "overeenkomst", niet "zekerheid", en onder de tabel staat dat een hoge score **niet** betekent dat
   de stof bewezen is.
2. Er is altijd een **top 5**, geen enkel antwoord.
3. De **overlay** dwingt je om zelf te kijken of het referentiespectrum echt past.
4. De **"eerlijke test"**-schakelaar laat zien dat de 100% bij een voorbeeldbestand komt doordat het bestand zelf in
   de bibliotheek staat.

## 3. Veiligheid

**De app mag nooit de enige basis zijn om een gevaarlijke of onbekende stof te identificeren.** Voorbeelden van
situaties waarin dat ernstige gevolgen kan hebben: een onbekende stof in een lekkend vat, vermoedelijke
verdovende middelen, een grondstof die vrijgegeven wordt voor productie, of een stof waarvan het veiligheidsblad
afhangt van de identificatie. Een fout ("aceton" terwijl het een giftig isomeer of een mengsel is) kan leiden tot
verkeerde beschermingsmaatregelen.

Daarom:
- staat bovenaan elke pagina van de app de disclaimer *"Hulpmiddel, geen bewijs … Gebruik hem nooit als enige basis
  om een onbekende of gevaarlijke stof te identificeren; laat de uitkomst altijd beoordelen door iemand met
  vakkennis en bevestig met een tweede techniek"* (getest in `tests/test_app.py`);
- noemt de waarschuwing bij een kleine voorsprong concreet aanvullende technieken (kookpunt, MS, NMR).

## 4. Bronvermelding en gebruiksvoorwaarden van de data

- De referentiespectra komen uit het **NIST Chemistry WebBook (NIST Standard Reference Database 69)**. Elk bestand
  vermeldt zelf: *"Collection (C) 2018 copyright by the U.S. Secretary of Commerce on behalf of the United States of
  America. All rights reserved."* NIST is de eigenaar; de data is niet vrij te herverspreiden.
- De bestanden zijn verzameld door **NistChemData** (Ivan Chernyshov). Dat is een **onofficiële** verzameling, geen
  product van NIST.
- **Belangrijk:** de auteur van NistChemData heeft in **mei 2026 alle databestanden uit de repository verwijderd**,
  juist om NIST-data niet meer te herverspreiden (zie de `DATA_NOTICE.md` van <https://github.com/muCommons/NistChemData>).
  Het archief staat nog in oudere forks. **De student heeft er zelf voor gekozen** het archief uit zo'n fork te halen
  (keuze tijdens het project, zie `docs/ai_logboek.md`). Het script controleert met een SHA-256-controlegetal dat het
  precies het oorspronkelijke bestand is.
- Hoe is daar verantwoord mee omgegaan?
  - De volledige database staat **niet** in de git-repository (`.gitignore`); iedereen downloadt hem zelf lokaal.
  - Alleen **tien** voorbeeldbestanden staan in de repository (`research/voorbeeldspectra/`), als klein voorbeeld voor
    onderwijs en om de tests te kunnen draaien. Bij publicatie van de repository moet worden afgewogen of dat mag;
    zonder die tien bestanden werken de tests met echte spectra niet.
  - Het gebruik is **lokaal en voor onderwijs**, niet commercieel.
  - Bronvermelding staat in de README, in de zijbalk van de app en in de voorbeeldmap.
- **Open vraag (zelf beoordelen):** is het ophalen van data die de verzamelaar bewust heeft teruggetrokken ethisch
  verantwoord, ook al gaat het om publiek raadpleegbare NIST-data en om onderwijsgebruik? Overleg dit eventueel met
  de docent.

## 5. Transparantie: de app laat zien waarom hij iets concludeert

| Wat de gebruiker ziet | Waarom dat transparant is |
|---|---|
| Rode stippen bij de gevonden pieken, met golfgetal | Je ziet waar de app naar kijkt |
| Overlay van referentie en monster | Je kunt de gelijkenis zelf beoordelen |
| Functionele groepen met de piek als reden ("C=O-rek: piek bij 1742 cm⁻¹") en een zekerheid | Elke conclusie is terug te voeren op een meetbaar kenmerk |
| Uitklapblok "Hoe komt de app tot dit resultaat?" | De vijf stappen in gewone taal, plus de rekentijd per stap |
| Keuze tussen drie vergelijkingsmethoden | Je ziet hoe gevoelig de uitkomst voor de methode is |
| Fase van elk referentiespectrum in de top 5 | Je ziet of de referentie in dezelfde fase is gemeten als jouw monster |

Omdat het systeem **niet getraind** is, is er geen "zwarte doos": elke stap is een vaste rekenregel die in de code
(met Nederlands commentaar) en in het notebook na te lezen is.

## 6. Privacy

De app slaat geüploade spectra niet op en stuurt niets naar internet: alles draait lokaal op de eigen computer.
Streamlit-gebruiksstatistieken staan uit (`.streamlit/config.toml`).

## Richtvragen voor je eigen reflectie (LU3)

- Welke beslissing in jouw toekomstige werk zou je níét op deze app willen baseren, en waarom?
- Hoe zou je een collega uitleggen dat 92% overeenkomst geen 92% kans op juist betekent?
- Vind je het verantwoord dat de data uit een fork is gehaald nadat de verzamelaar hem had verwijderd? Wat zou je
  anders doen als de app commercieel gebruikt zou worden?
- Wie is verantwoordelijk als een laborant op basis van de app een verkeerde stof noteert?
- Welke extra waarschuwing of functie zou het risico op blind vertrouwen het meest verkleinen?
