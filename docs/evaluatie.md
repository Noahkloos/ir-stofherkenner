# Evaluatie van de spectra-matching

> Dit bestand is automatisch gemaakt door `scripts/evaluatie.py` op 2026-11-16.
> Alle getallen komen uit een echte run op de volledige bibliotheek; er is niets met de hand ingevuld.
> Opnieuw draaien: `.venv\Scripts\python scripts\evaluatie.py`

## Opzet

- Bibliotheek: **18016 unieke spectra** van **15817 stoffen** (resolutie-duplicaten zijn weggelaten, zie hieronder).
- Testset: alle stoffen met minstens twee echt verschillende spectra: **1735 stoffen, 3934 spectra**.
- Methode ("leave-one-out"): elk testspectrum wordt een keer uit de bibliotheek gehaald en als "onbekend monster"
  gebruikt. We zoeken ermee in de rest van de bibliotheek (18015 spectra) en kijken op welke plek de juiste stof staat.
  De ranglijst telt in *stoffen*: van elke stof telt alleen het best passende spectrum.
- **Top-1** = de juiste stof staat op plek 1. **Top-5** = de juiste stof staat bij de eerste vijf.

### Waarom duplicaten weglaten?

Van sommige stoffen staat dezelfde meting meerdere keren in de NIST-data, alleen met een andere resolutie
(vooral in de reeks QUANT-IR). Als je zo'n spectrum eruit haalt, vindt de zoekactie direct zijn "tweelingbroer"
terug. Dat is geen eerlijke test: je meet dan niet of de app een stof herkent, maar of hij een kopie herkent.
Daarom is een spectrum als duplicaat gemarkeerd (en hier weggelaten) als het van dezelfde stof is én
(a) de cosinusgelijkenis met een eerder spectrum van die stof >= 0,99 is, of (b) beide uit de QUANT-IR-resolutiereeks komen.
Regel (a) is streng: ook twee onafhankelijke metingen die toevallig bijna identiek zijn vallen weg.
De cijfers hieronder zijn daardoor eerder te voorzichtig dan te rooskleurig.

## Resultaten per methode

| Methode | Geteste spectra | Top-1 | Top-5 | Top-1 als er een ander spectrum in dezelfde fase is | Top-1 als de stof alleen in een andere fase voorkomt | Zoektijd (mediaan) | Zoektijd (max) |
|---|---|---|---|---|---|---|---|
| cosinus | 3934 | **52.9%** | **69.5%** | 85.5% | 40.7% | 22.5 ms | 28.1 ms |
| pearson | 3934 | **52.9%** | **69.5%** | 85.5% | 40.7% | 35.2 ms | 43.2 ms |
| euclidisch | 3934 | **49.4%** | **65.0%** | 82.9% | 36.9% | 24.3 ms | 31.1 ms |

De zoektijd is gemeten over 50 zoekopdrachten door de hele bibliotheek (18016 spectra) op de laptop waarop
deze evaluatie is gedraaid, inclusief het maken van de top 5. De eis was: binnen 1 seconde (1000 ms).

**Gekozen standaardmethode voor de app: `cosinus`.** Keuzeregel: de hoogste top-1; als het verschil met
cosinus kleiner is dan 0,5 procentpunt kiezen we cosinus, omdat die het eenvoudigst uit te leggen en het snelst is.

Alle methoden werken op de "vergelijkingsvorm" van het spectrum (logaritme + eerste afgeleide). Waarom, en hoeveel
dat scheelt ten opzichte van de kale absorbantie, staat in [vergelijking_voorbewerking.md](vergelijking_voorbewerking.md).

### Controle: is er niet "afgesteld op de testset"?

Eerlijke kanttekening: het *idee* om compressie en een afgeleide te gebruiken kwam uit een eerste verkenning op de
hele testset (zie `docs/ai_logboek.md`). Daarna is de stoffenlijst in twee vaste helften gesplitst en zijn de
*details* (soort compressie, logfactor, venster van de afgeleide) alleen op de afstelhelft gekozen. De controlehelft
is dus niet helemaal "onaangeroerd". Resultaat van `cosinus` per helft:

| Deel van de testset | Aantal spectra | Top-1 | Top-5 |
|---|---|---|---|
| afstelhelft (details van de voorbewerking hierop gekozen) | 1882 | 54.0% | 69.7% |
| controlehelft (niet gebruikt voor de details; wel in de eerste verkenning) | 2052 | 51.9% | 69.3% |

De cijfers van de controlehelft zijn het eerlijkst. Liggen ze duidelijk lager dan die van de afstelhelft, dan zijn de
details te veel op de afstelhelft afgesteld (overfitting). Een klein verschil wijst erop dat de keuze ook voor nieuwe
stoffen werkt, maar omdat de grote ontwerpkeuze op alle data is verkend, is dit geen volledig onafhankelijke toets.

## Invloed van de fase (methode: cosinus)

| Fase van het testspectrum | Aantal | Top-1 | Top-5 |
|---|---|---|---|
| gas | 1638 | 41.6% | 58.3% |
| vloeistof | 502 | 58.0% | 77.5% |
| oplossing | 1053 | 67.2% | 83.0% |
| vast | 669 | 54.3% | 68.8% |
| onbekend | 72 | 52.8% | 77.8% |

Bij 1074 van de 3934 testspectra bestaat er een ander spectrum van dezelfde stof in dezelfde fase;
bij de overige 2860 is de juiste stof alleen in een ándere fase aanwezig (bijv. test = gas, referentie = vaste stof).
Het verschil in top-1 tussen die twee groepen (zie tabel hierboven) laat zien hoe sterk de fase het spectrum verandert.

## Analyse van de fouten (methode: cosinus)

Aantal testspectra waarbij een verkeerde stof op plek 1 stond: **1853 van de 3934** (47.1%).
Bij 91.6% van deze fouten was de juiste stof alleen in een andere fase beschikbaar.

Opvallend: bij 1 testspectra staat er onder de naam van een ándere stof een (vrijwel) identiek
spectrum in de bibliotheek (score >= 99,9%). Daarvan gingen er 1 fout. Dit zijn fouten of
dubbelingen in de brondata (bijv. hetzelfde spectrum bij twee isomeren of onder twee namen); daar kan geen enkele
zoekmethode iets aan doen.

Hoe verhoudt de foute nummer 1 zich tot de juiste stof (op basis van de molecuulformule)?

| Soort verwarring | Aantal | Aandeel van de fouten |
|---|---|---|
| homologe reeks (verschilt alleen een of meer CH2-groepen) | 694 | 37.5% |
| andere samenstelling | 574 | 31.0% |
| zelfde elementen, andere aantallen | 452 | 24.4% |
| isomeer (zelfde molecuulformule) | 130 | 7.0% |
| onbekend (formule ontbreekt) | 3 | 0.2% |

### Voorbeelden van fouten

| Testspectrum (juiste stof) | Foute nummer 1 | Score foute stof | Score juiste stof | Plek juiste stof | Verklaring |
|---|---|---|---|---|---|
| Ethane, 1,1,2-trichloro-1,2,2-trifluoro- (C 2 Cl 3 F 3, gas) | Ethane, 1,1,1-trichloro-2,2,2-trifluoro- (C 2 Cl 3 F 3, gas) | 99.9% | 90.4% | 2 | isomeer (zelfde molecuulformule) |
| 2-Cyclohexen-1-one, 2-methyl-5-(1-methylethenyl)-, (S)- (C 10 H 14 O, gas) | 2-Cyclohexen-1-one, 2-methyl-5-(1-methylethenyl)-, (R)- (C 10 H 14 O, gas) | 99.3% | 56.3% | 7 | isomeer (zelfde molecuulformule) |
| 1-Decanol acetate (C 12 H 24 O 2, gas) | 1-Dodecanol acetate (C 14 H 28 O 2, gas) | 99.6% | 83.8% | 24 | homologe reeks (verschilt alleen een of meer CH2-groepen) |
| 1,10-Undecadiene (C 11 H 20, gas) | 1,11-Dodecadiene (C 12 H 22, gas) | 99.3% | 71.3% | 55 | homologe reeks (verschilt alleen een of meer CH2-groepen) |
| 1,1-DIFLUORO-1,2,2,2-TETRACHLORO ETHANE (C2 Cl4 F2, oplossing) | PENTACHLORO FLUORO ETHANE (C2 Cl5 F, oplossing) | 98.6% | 83.7% | 2 | zelfde elementen, andere aantallen |
| Phenol, 2,6-dichloro- (C 6 H 4 Cl 2 O, gas) | 3,5-Dichloro-4-hydroxybenzoic acid (C 7 H 4 Cl 2 O 3, gas) | 98.4% | 57.2% | 4 | zelfde elementen, andere aantallen |
| Mepivacaine (C 15 H 22 N 2 O, gas) | Mafenide (C 7 H 10 N 2 O 2 S, gas) | 97.6% | 70.3% | 2 | andere samenstelling |
| Isoquinoline (C 9 H 7 N, gas) | 1-Isoquinolinecarboxylic acid (C 10 H 7 N O 2, gas) | 97.4% | 72.3% | 2 | andere samenstelling |
| 1-Decanol acetate (C 12 H 24 O 2, gas) | 1-Dodecanol acetate (C 14 H 28 O 2, gas) | 99.6% | 83.8% | 24 | andere fase: referentie van de juiste stof alleen als vloeistof |
| 2-Cyclohexen-1-one, 2-methyl-5-(1-methylethenyl)-, (S)- (C 10 H 14 O, gas) | 2-Cyclohexen-1-one, 2-methyl-5-(1-methylethenyl)-, (R)- (C 10 H 14 O, gas) | 99.3% | 56.3% | 7 | andere fase: referentie van de juiste stof alleen als oplossing |

Verklaring in gewone taal:
- **Isomeren** hebben dezelfde atomen en vaak dezelfde functionele groepen; hun IR-spectra verschillen dan alleen
  in details in het "fingerprint"-gebied (onder ~1500 cm⁻¹).
- **Homologe reeksen** (bijv. opeenvolgende alkanen, alcoholen of esters die alleen een CH₂-groep verschillen)
  hebben bijna hetzelfde spectrum: dezelfde groepen, alleen een iets andere verhouding C–H tegenover de rest.
- **Andere fase**: in gasfase zijn pieken smaller en verschoven en ontbreken waterstofbruggen (vrije O–H rond
  3650 cm⁻¹ in plaats van een brede band rond 3200–3550 cm⁻¹). Een gasspectrum lijkt daardoor soms meer op het
  gasspectrum van een verwante stof dan op het vloeistofspectrum van zichzelf.

## Hoe betrouwbaar is de score? (methode: cosinus)

Verdeling van de score (percentielen):

| Situatie | 5% | 25% | mediaan | 75% | 95% |
|---|---|---|---|---|---|
| Score op plek 1, juiste stof gevonden (2081x) | 62.3% | 75.1% | 82.0% | 88.8% | 95.5% |
| Score op plek 1, verkeerde stof op plek 1 (1853x) | 52.1% | 67.2% | 80.6% | 89.1% | 97.0% |
| Beste score als de juiste stof NIET in de bibliotheek zit (gesimuleerd, 3934x) | 48.7% | 58.9% | 69.7% | 81.8% | 94.6% |
| Verschil tussen nummer 1 en 2, juiste stof gevonden | 1.3% | 7.0% | 15.3% | 25.5% | 39.7% |
| Verschil tussen nummer 1 en 2, verkeerde stof op plek 1 | 0.1% | 0.9% | 2.4% | 5.2% | 12.7% |

De regel "stof niet in de bibliotheek" is gesimuleerd door alle spectra van de juiste stof weg te denken en te kijken
wat dan de hoogste score is.

**Belangrijkste les:** ook als de stof helemaal niet in de bibliotheek zit, vindt de app bijna altijd iets met een
hoge score. Een hoge score is dus géén bewijs dat de stof juist is.

### Waarschuwingen in de app

De app waarschuwt als de beste score lager is dan **65%** en als nummer 1 en 2 minder dan
**5.0 procentpunt** van elkaar liggen. Gemeten effect op de testset:

| | Juiste stof op plek 1 | Verkeerde stof op plek 1 | Juiste stof niet in bibliotheek (gesimuleerd) |
|---|---|---|---|
| Waarschuwing "lage score" | 7.2% | 22.2% | 40.0% |
| Waarschuwing "nummer 1 en 2 dicht bij elkaar" | 17.7% | 74.2% | n.v.t. |
| Minstens een van beide waarschuwingen | 21.4% | 78.4% | n.v.t. |

Lees dit als: bij een verkeerd antwoord geeft de app in 78.4% van de gevallen een waarschuwing,
maar in 21.6% van de foute antwoorden dus níet. En bij een goed antwoord waarschuwt de app
in 21.4% van de gevallen onterecht. De waarschuwingen helpen, maar vervangen het oordeel van de
laborant niet.

## Beperkingen van deze evaluatie

- De test gebruikt NIST-spectra als "onbekend monster". Een eigen meting (ander apparaat, ATR, vervuild monster,
  mengsel) wijkt meer af dan een tweede NIST-spectrum. In de praktijk zal de nauwkeurigheid dus lager uitvallen.
- Alleen stoffen met minstens twee verschillende spectra konden getest worden (1735 van de 15817 stoffen).
  Dat zijn vooral bekende, veelgebruikte stoffen.
- Stoffen die niet in de bibliotheek staan kan de app per definitie niet vinden.
- De fase-indeling komt uit het vrije tekstveld `##STATE` van de bestanden en is automatisch in vijf groepen ingedeeld.

Totale rekentijd van deze evaluatie: 32 s.
