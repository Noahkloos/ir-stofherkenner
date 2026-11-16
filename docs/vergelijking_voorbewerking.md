# Vergelijking van voorbewerkingsvarianten voor de matching

> Automatisch gemaakt door `scripts/vergelijk_voorbewerking.py` op 2026-11-16.
> Alle getallen komen uit een echte run. Opnieuw draaien: `.venv\Scripts\python scripts\vergelijk_voorbewerking.py`

## Waarom dit onderzoek?

De eerste versie van de matching vergeleek de kale, genormaliseerde absorbantie. Dat gaf een teleurstellende
top-1-nauwkeurigheid. Twee bekende zwakke punten van die aanpak:

1. **De hoogste piek domineert.** Piekhoogtes hangen af van concentratie, laagdikte en fase; piekposities veel minder.
   Oplossing: de hoogtes samendrukken (*compressie*), zodat zwakke pieken zwaarder meetellen.
2. **De basislijn telt mee.** Vaste stoffen en oude metingen hebben vaak een scheve of verhoogde basislijn.
   Oplossing: de *eerste afgeleide* (helling) vergelijken; een langzaam verlopende basislijn heeft bijna geen helling.

## Opzet

- Zelfde leave-one-out-test als in [evaluatie.md](evaluatie.md), met cosinusgelijkenis.
- De stoffen zijn vast in twee helften verdeeld. **De varianten in de tabel hieronder zijn alleen op de afstelhelft
  vergeleken** (1882 testspectra). De controlehelft (2052 testspectra) is daarna alleen gebruikt
  voor de gekozen variant.
- **Eerlijke kanttekening:** vóór deze splitsing is in een eerste verkenning op de hele testset al gezien dat
  "wortel/log + afgeleide" veel beter werkt dan de kale absorbantie. De grote ontwerpkeuze is dus op alle data
  verkend; alleen de details (soort compressie, factor, venster) zijn zuiver op de afstelhelft gekozen.
  De controlehelft is daardoor geen volledig onafhankelijke toets. Zie `docs/ai_logboek.md`.
- Ruistest: bij het testspectrum is willekeurige ruis opgeteld (standaarddeviatie 1% en 3% van de hoogste piek)
  om te zien of een variant niet alleen op "schone" NIST-spectra werkt.

## Resultaten op de afstelhelft (cosinus)

| Variant | Top-1 | Top-5 | Top-1 met 1% ruis | Top-1 met 3% ruis |
|---|---|---|---|---|
| kale absorbantie (uitgangssituatie) | 30.1% | 43.5% | 28.6% | 17.8% |
| alleen wortel | 29.7% | 43.1% | 20.4% | 5.0% |
| alleen logaritme | 22.4% | 33.4% | 9.1% | 1.3% |
| alleen afgeleide | 34.6% | 48.4% | 34.9% | 34.8% |
| wortel + afgeleide | 47.0% | 62.9% | 45.7% | 44.3% |
| derdemachtswortel + afgeleide | 50.3% | 65.8% | 49.2% | 46.9% |
| logaritme + afgeleide (venster 9) | 54.0% | 69.7% | 52.0% | 48.8% |
| logaritme + afgeleide (venster 5) | 51.9% | 68.2% | 49.8% | 46.9% |
| logaritme + afgeleide (venster 13) | 51.2% | 67.9% | 49.9% | 47.4% |

## Keuze

Gekozen instelling in `stofherkenner/voorbewerking.py`: **compressie = `log`, afgeleide met venster 9**.

## Bevestiging op de controlehelft

| | Afstelhelft top-1 / top-5 | Controlehelft top-1 / top-5 |
|---|---|---|
| Kale absorbantie (uitgangssituatie) | 30.1% / 43.5% | 31.0% / 43.9% |
| Gekozen instelling | 54.0% / 69.7% | 51.9% / 69.3% |

De controlehelft is niet gebruikt bij het kiezen van de details. Als de winst daar ongeveer even groot is als op de
afstelhelft, zijn die details niet "op toeval" afgesteld. (De grote keuze voor compressie + afgeleide is wel op alle
data verkend; zie de kanttekening bij "Opzet".)

## Kanttekeningen

- Er is bewust maar een klein aantal varianten geprobeerd. Hoe meer varianten je op dezelfde data probeert, hoe
  groter de kans dat de beste "toevallig" goed scoort.
- De ruistest gebruikt kunstmatige, gelijkmatige ruis. Echte meetfouten (waterdamp, CO₂, ATR-effecten) zijn
  anders van aard en zijn hier niet getest.
- Logaritmische compressie maakt de score gevoeliger voor kleine piekjes. Bij een erg ruizig spectrum kan dat
  nadelig zijn; de ruistest hierboven laat zien hoeveel de nauwkeurigheid dan daalt.

Rekentijd: 119 s.
