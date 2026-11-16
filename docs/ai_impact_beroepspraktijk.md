# AI-impact op de beroepspraktijk van laborant en analist

Hoort bij **LU1** (AI-impact op de beroepspraktijk analyseren en evalueren).

> **[CONCEPT – zelf nalezen en aanvullen]** Opgesteld door de AI-assistent op basis van de meetresultaten van dit
> project. De analyse van de beroepspraktijk (hoe gaat het nu op een lab?) moet je zelf aanvullen met eigen ervaring,
> stage of een gesprek met een laborant. Alle cijfers hieronder komen uit echte runs; de bronbestanden staan erbij.

## 1. Hoe gaat het nu? (zelf aanvullen)

Een laborant die een onbekend IR-spectrum moet interpreteren doet ongeveer het volgende:

1. pieken aflezen en met een correlatietabel functionele groepen bepalen;
2. op basis daarvan kandidaat-stoffen bedenken;
3. referentiespectra opzoeken (boek, NIST WebBook, bibliotheek van de spectrometersoftware) en visueel vergelijken;
4. eventueel bevestigen met een tweede techniek (GC-MS, NMR, smeltpunt, kookpunt).

*[Aanvullen: hoe gebeurt dit op jouw stage of in een lab dat je kent? Welke software gebruiken ze (veel spectrometers
hebben een eigen commerciële zoekbibliotheek)? Hoe lang duurt stap 1–3 ongeveer?]*

## 2. Wat verandert er met een tool als de IR-Stofherkenner?

### Tijdwinst en minder handwerk

| Stap | Zonder tool | Met tool (gemeten) | Bron |
|---|---|---|---|
| Bestand controleren, inlezen en grafiek tonen | handmatig in software | 229 ms gemeten in de app voor het ethanolvoorbeeld; ongeveer 0,4–0,5 s voor een bestand van 4,84 MB (verschilt iets per run, zie `docs/testresultaten.md`) (rekenwerk van de server; tekenen in de browser niet apart gemeten) | `docs/testresultaten.md` |
| Vergelijken met referenties | één voor één zoeken en vergelijken | ± 23 ms voor alle 18.016 referentiespectra (mediaan, cosinus) | `docs/evaluatie.md` |
| Functionele groepen bepalen | correlatietabel naast het spectrum | direct, met de piek als reden | app |

De grootste tijdwinst zit in het **zoeken en vergelijken**: in plaats van een paar zelfgekozen kandidaten wordt de hele
bibliotheek doorzocht. Daardoor komen ook kandidaten in beeld waar de laborant zelf niet aan had gedacht.

### Hoe goed is de "shortlist"?

Uit de leave-one-out-evaluatie op 3.934 spectra van 1.735 stoffen (`docs/evaluatie.md`):

| | Top-1 | Top-5 |
|---|---|---|
| Alle testspectra | 52,9% | 69,5% |
| Er bestaat een referentie in **dezelfde fase** als het monster | 85,5% | – |
| De stof is alleen in een **andere fase** gemeten | 40,7% | – |

Met een referentie in dezelfde fase is de tool dus een sterke hulp; staat jouw stof er alleen als gasspectrum in
terwijl je een vloeistof meet, dan is hij in minder dan de helft van de gevallen direct goed. In de praktijk (eigen
apparaat, ATR, onzuiverheden) zal het lager uitvallen dan in deze test met NIST-spectra.

## 3. Risico's

### Blind vertrouwen

- Een foute nummer 1 krijgt gemiddeld bijna dezelfde score als een goede: mediaan **80,6%** tegenover **82,0%**.
- Bij **22%** van de foute antwoorden geeft de app géén waarschuwing (`docs/evaluatie.md`).
- Voorbeeld: butylamine → *1,5-pentaandiamine* (80,5%), zonder waarschuwing (`docs/demo_eerlijke_test.txt`).

Een laborant die de bovenste regel overneemt zonder te kijken, zal dus regelmatig een verkeerde stof noteren. Hoe
makkelijker en sneller een tool is, hoe groter de verleiding om niet meer zelf te kijken (*automation bias*).

### Verlies van vakkennis

Als het interpreteren van spectra niet meer geoefend wordt, wordt het moeilijker om fouten van de tool te herkennen.
De tool is juist het meest waard in handen van iemand die het spectrum zelf ook kan lezen.

### Schijnzekerheid buiten de database

Een stof die niet in de bibliotheek staat krijgt toch een "beste match", met in de helft van de gevallen een score
boven 69,7% (gesimuleerd, `docs/evaluatie.md`).

## 4. De rol van vakkennis blijft groot

| Taak | Tool | Laborant |
|---|---|---|
| Hele bibliotheek doorzoeken | ✅ snel en volledig | ❌ onhaalbaar |
| Pieken vinden en groepen voorstellen | ✅ consistent | ✅ kan context meenemen (monstervoorbereiding, oplosmiddel) |
| Beoordelen of de match chemisch klopt (herkomst van het monster, fase, verwachte stoffen) | ❌ | ✅ |
| Isomeren en homologen uit elkaar houden | ❌ vaak niet | ✅ met aanvullende technieken |
| Mengsels herkennen | ❌ | ✅ |
| Verantwoordelijkheid voor de uitslag | ❌ | ✅ |

De verschuiving: van **zoeken** naar **beoordelen**. De laborant besteedt minder tijd aan opzoeken en meer aan de
vraag "klopt dit, en hoe bevestig ik het?".

## 5. Conclusie (concept)

De tool kan het werk van een laborant versnellen door in milliseconden een onderbouwde shortlist te geven, met uitleg
in functionele groepen. Hij is betrouwbaar genoeg om als **eerste stap** te gebruiken (ongeveer 7 op de 10 keer zit de
juiste stof in de top 5), maar niet om zelfstandig te beslissen (ongeveer de helft van de nummers 1 is fout, vaak
zonder dat de score dat laat zien). Het verantwoord inzetten vraagt om duidelijke werkafspraken: de tool levert
kandidaten, de laborant beslist en bevestigt met een tweede techniek.

*[Aanvullen: jouw eigen conclusie. Zou je deze tool op jouw stage willen gebruiken? Onder welke voorwaarden?]*

## Richtvragen voor je eigen reflectie (LU1)

- Welke taken van een laborant worden door zo'n tool overbodig, en welke juist belangrijker?
- Zou je de tool laten gebruiken door een beginnende laborant? Waarom wel of niet?
- Hoe meet je in de praktijk of de tool echt tijd bespaart (en niet alleen het zoeken verschuift naar controleren)?
- Wat zou er moeten veranderen (data, fase, eigen bibliotheek) voordat je de tool in een gecertificeerd lab zou inzetten?
