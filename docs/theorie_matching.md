# Theorie: spectra vergelijken (matching)

Hoort bij user story **LS**. Uitwerking met grafieken: [`notebooks/piekdetectie_en_matching.ipynb`](../notebooks/piekdetectie_en_matching.ipynb).
De code staat in [`stofherkenner/matching.py`](../stofherkenner/matching.py).

## 1. Het idee: een spectrum is een rij getallen

Na de voorbewerking staat elk spectrum op hetzelfde raster: 813 punten, van 550 tot 3798 cm⁻¹ in stappen van
4 cm⁻¹. Een spectrum is dan gewoon een rij van 813 getallen. Zo'n rij kun je zien als een **pijl (vector)** in een
ruimte met 813 richtingen. Twee spectra die op elkaar lijken zijn twee pijlen die dicht bij elkaar liggen of dezelfde
kant op wijzen. "Spectral library search" betekent: het onbekende spectrum vergelijken met élk spectrum in de
bibliotheek en de best passende bovenaan zetten.

Klein rekenvoorbeeld (drie punten in plaats van 813), dat ook in het notebook en in
`tests/test_matching.py::test_handmatig_nagerekend_voorbeeld` staat:

```
a = (1, 2, 3)        b = (2, 2, 1)
```

## 2. Drie methoden

### Euclidische afstand – "hoe ver liggen de punten uit elkaar?"

De gewone afstand (stelling van Pythagoras, maar in 813 dimensies):

    d = wortel( (a1−b1)² + (a2−b2)² + ... )

Voorbeeld: d = wortel(1 + 0 + 4) = wortel(5) ≈ 2,24. Hoe kleiner, hoe meer gelijk; 0 = identiek.
De app zet dit om naar een score: 100% × (1 − gemiddelde afwijking per punt).

- ✅ Heel intuïtief: "het verschil tussen de lijnen".
- ❌ Gevoelig voor de **sterkte** van het spectrum. Een twee keer zo dik monster geeft een twee keer zo hoge lijn en
  dus een grote afstand, terwijl het dezelfde stof is. Normaliseren helpt, maar niet helemaal.

### Cosinusgelijkenis – "wijzen de pijlen dezelfde kant op?"

    cos(hoek) = (a1·b1 + a2·b2 + ...) / ( lengte(a) × lengte(b) )

Voorbeeld: (2 + 4 + 3) / (wortel(14) × wortel(9)) = 9 / 11,2 ≈ 0,80 → 80%.
1 (100%) = precies dezelfde vorm, 0 = niets gemeen.

- ✅ **De lengte van de pijl telt niet mee:** een sterker of zwakker spectrum van dezelfde stof geeft dezelfde score.
- ✅ Eenvoudig, snel en veel gebruikt in spectrale zoeksystemen.
- ❌ Een verschoven basislijn (alles een stukje hoger) verandert de richting wel, en dus de score.

### Pearson-correlatie – "gaan ze samen omhoog en omlaag?"

Precies de cosinusgelijkenis, maar eerst wordt van elk spectrum zijn eigen **gemiddelde afgetrokken**.

- ✅ Ongevoelig voor sterkte én voor een constante verschuiving van de basislijn.
- ❌ Iets meer rekenwerk; een scheve (niet-constante) basislijn blijft een probleem.

## 3. Twee praktische details

**Alleen het gemeenschappelijke stuk vergelijken.** Niet elk spectrum is over het hele bereik gemeten (sommige stoppen
bij 650 cm⁻¹). De app houdt per spectrum een *masker* bij (welke punten echt gemeten zijn) en vergelijkt alleen het
stuk dat beide spectra gemeten hebben. Is dat stuk korter dan 1200 cm⁻¹, dan is de score 0.

**Gevectoriseerd rekenen.** Een lus over 18.016 spectra is in Python traag. De app schrijft de sommen uit de formules
als **matrixvermenigvuldigingen** (`@` in numpy), zodat alle 18.016 vergelijkingen in één keer gebeuren.
Gemeten zoektijd: zie de tabel in [`evaluatie.md`](evaluatie.md) (ruim onder de eis van 1 seconde).

## 4. Niet de kale absorbantie, maar de "vergelijkingsvorm"

De eerste versie vergeleek de genormaliseerde absorbantie. Twee problemen:

1. **De hoogste piek bepaalt bijna de hele score.** Piekhoogtes hangen af van concentratie, laagdikte en fase; de
   *posities* zijn veel betrouwbaarder. → De hoogtes worden eerst **logaritmisch samengedrukt**
   (log(1 + 100·A)), zodat ook zwakke pieken meetellen.
2. **De basislijn telt mee.** → Daarna wordt de **eerste afgeleide** (de helling, met een Savitzky-Golay-filter van
   9 punten) vergeleken. Een langzaam verlopende of scheve basislijn heeft bijna geen helling en valt weg.

Het effect is gemeten in [`vergelijking_voorbewerking.md`](vergelijking_voorbewerking.md).

## 5. Welke methode gebruikt de app, en waarom?

Gemeten met de leave-one-out-evaluatie op 3.934 testspectra van 1.735 stoffen (`scripts/evaluatie.py`):

| Vergelijking op… | Methode | Top-1 | Top-5 |
|---|---|---|---|
| kale absorbantie (eerste versie) | cosinus | 30,6% | 43,7% |
| kale absorbantie (eerste versie) | Pearson | 31,8% | 45,8% |
| kale absorbantie (eerste versie) | Euclidisch | 25,1% | 36,8% |
| **vergelijkingsvorm (huidige versie)** | **cosinus** | **52,9%** | **69,5%** |
| vergelijkingsvorm | Pearson | 52,9% | 69,5% |
| vergelijkingsvorm | Euclidisch | 49,4% | 65,0% |

De cijfers voor de kale absorbantie komen uit de eerste run van `scripts/evaluatie.py` (vóór de vergelijkingsvorm;
zie het logboek). De actuele cijfers staan altijd in [`evaluatie.md`](evaluatie.md).

**Keuze: cosinusgelijkenis op de vergelijkingsvorm.**

- Euclidisch scoort duidelijk het slechtst, zoals verwacht: het is gevoelig voor sterkteverschillen.
- Cosinus en Pearson zijn op de vergelijkingsvorm **even goed**. Dat is logisch: het gemiddelde van een afgeleide is
  bijna nul, dus "gemiddelde aftrekken" (het enige verschil met cosinus) verandert nauwelijks iets.
- Bij gelijke nauwkeurigheid kiezen we de **eenvoudigste en snelste** methode: cosinus (geen extra sommen nodig,
  en het makkelijkst uit te leggen: "de hoek tussen twee pijlen").

In de app kan de gebruiker in de zijbalk ook Pearson of Euclidisch kiezen, om te zien hoe de uitkomst verandert.

## 6. Wat matching níét kan

- Een stof die niet in de bibliotheek staat, wordt nooit gevonden. De app geeft dan wel een "beste" match, vaak een
  verwante stof. Een hoge score is dus **geen bewijs** (zie de scoreverdelingen in `evaluatie.md`).
- Een **mengsel** lijkt op geen enkel zuiver spectrum goed.
- Spectra in een **andere fase** (gas tegenover vloeistof/vast) wijken af: in de evaluatie is top-1 duidelijk hoger
  als er een referentie in dezelfde fase bestaat.
