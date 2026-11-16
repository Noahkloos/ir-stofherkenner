# Controle van de functionele-groepenregels

> Automatisch gemaakt door `scripts/controle_functionele_groepen.py` op 2026-11-16.
> Alle getallen komen uit een echte run op de 18016 unieke spectra in de bibliotheek.
> Opnieuw draaien: `.venv\Scripts\python scripts\controle_functionele_groepen.py`

## Hoe is dit getest?

De bibliotheek vertelt niet per stof welke functionele groepen erin zitten. We gebruiken daarom:

- **De naam** om stoffen te vinden waar de groep in *hoort* te zitten (bijv. "...nitrile", "...ol", "...acetate").
  Het percentage van die spectra waarbij de regel afgaat is de **trefkans**. Naamherkenning is grof, dus dit is
  een indicatie.
- **De molecuulformule** om stoffen te vinden waar de groep *onmogelijk* in kan zitten (bijv. geen stikstof → geen
  nitril). Gaat de regel daar toch af, dan is dat zeker een **vals alarm**. Dit percentage is exact.

## Resultaat per regel

| Groep | Spectra waar de groep volgens de naam in zit | Trefkans (elke zekerheid) | Trefkans (middel of hoog) | Spectra waar de groep onmogelijk is | Vals alarm (elke zekerheid) | Vals alarm (middel of hoog) | Vals alarm (hoog) |
|---|---|---|---|---|---|---|---|
| O–H (alcohol of fenol) | 2049 | 73% | 57% | 5510 (geen zuurstof in de formule) | 7% | 6% | 4% |
| Carbonzuur (–COOH) | 1075 | 63% | 63% | 9572 (minder dan twee zuurstofatomen) | 1% | 1% | 0% |
| C=O (keton of aldehyde) | 1786 | 80% | 72% | 5941 (geen zuurstof, of verzadigd (CnH2n+2)) | 1% | 1% | 1% |
| Ester (–COO–) | 1516 | 64% | 64% | 9716 (minder dan twee zuurstofatomen, of verzadigd) | 1% | 1% | 1% |
| N–H (amine) | 1184 | 48% | 19% | 9989 (geen stikstof in de formule) | 8% | 0% | 0% |
| C≡N (nitril) | 463 | 56% | 56% | 9989 (geen stikstof in de formule) | 1% | 1% | 0% |
| C=C (alkeen) | 1108 | 45% | 41% | 591 (verzadigd (CnH2n+2)) | 1% | 1% | 0% |
| Aromaat (benzeenring) | 6767 | 59% | 59% | 3295 (minder dan zes koolstofatomen, of verzadigd) | 9% | 9% | 1% |

## Gasfase tegenover vloeistof/vast/oplossing (trefkans, elke zekerheid)

| Groep | Aantal gas | Trefkans gas | Aantal niet-gas | Trefkans niet-gas |
|---|---|---|---|---|
| O–H (alcohol of fenol) | 1195 | 83% | 854 | 59% |
| Carbonzuur (–COOH) | 610 | 84% | 465 | 35% |
| C=O (keton of aldehyde) | 983 | 85% | 803 | 73% |
| Ester (–COO–) | 690 | 76% | 826 | 54% |
| N–H (amine) | 518 | 39% | 666 | 55% |
| C≡N (nitril) | 311 | 44% | 152 | 78% |
| C=C (alkeen) | 646 | 41% | 462 | 52% |
| Aromaat (benzeenring) | 3665 | 55% | 3102 | 63% |

## Hoe lees je dit?

- Een **hoge trefkans** betekent: als de groep er is, ziet de regel hem meestal.
- Een **laag vals alarm** betekent: als de regel afgaat, is dat zelden onzin.
- De zekerheid die de app toont (hoog / middel / laag) is bedoeld als rangorde: de kolommen "vals alarm" laten
  zien dat een melding met zekerheid *hoog* minder vaak onterecht is dan een met *laag*.
- Geen enkele regel is perfect. Daarom is dit in de app een **uitleg bij de top 5 en geen beslissing**.

Rekentijd: 21 s.
