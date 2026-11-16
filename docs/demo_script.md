# Demo-script (5 minuten)

Hoort bij **LU2** (presenteren). Alle uitkomsten hieronder komen uit echte runs; de "eerlijke test"-uitkomsten staan
volledig in [`demo_eerlijke_test.txt`](demo_eerlijke_test.txt) (gemaakt met `scripts/demo_eerlijke_test.py`).
Controleer vlak voor de presentatie of je dezelfde uitkomsten ziet.

**Voorbereiding:** `start.bat` openen, browser op <http://localhost:8501>, zijbalk open, "Eerlijke test" **uit**.
Houd `research\voorbeeldspectra\` open in de Verkenner, zodat je een bestand kunt slepen.

---

## 0:00 – 0:40 · Het probleem

> "Als laborant meet je een IR-spectrum en dan begint het puzzelen: welke pieken zie ik, welke groepen zijn dat, en
> welke stof past erbij? Dat vergelijken met referentiespectra kost veel tijd. Deze app doorzoekt in een fractie van
> een seconde ruim 18.000 NIST-referentiespectra en legt uit waarom hij iets denkt."

Wijs op de waarschuwing bovenaan: *hulpmiddel, geen bewijs*.

## 0:40 – 1:40 · Uploaden en grafiek (US)

1. **Sleep `ethylacetaat_gas_C141786_IR_0.jdx`** naar het uploadvak.
2. Laat zien: grafiek verschijnt direct, golfgetal van hoog naar laag, rode stippen bij de pieken
   (o.a. 1766 en 1242 cm⁻¹).
3. Vertel: *"Het bestand wordt eerst streng gecontroleerd. Kijk maar:"* → sleep een **.csv- of .txt-bestand** in
   het uploadvak. Laat de Nederlandse foutmelding zien ("Wat is er mis? / Wat kun je doen?").

## 1:40 – 2:40 · Top 5 en uitleg (matching + expertsysteem)

1. Upload weer ethylacetaat. Top 5: Ethyl Acetate bovenaan, daarna andere acetaat-esters.
2. Wijs op de melding *"Dit exacte spectrum staat zelf in de bibliotheek"* → zet **"Eerlijke test"** aan.
   Uitkomst in de eerlijke test: **Ethyl Acetate blijft op 1 (96,0%)**, nummer 2 is een andere acetaat (88,1%).
3. Scrol naar de **overlay**: standaard ligt nummer 1 over het monster. Kies in "Referenties over het spectrum
   leggen" ook de andere vier: alle vijf acetaat-esters lijken sterk op elkaar, vooral boven 1500 cm⁻¹.
3b. Scrol terug naar de grafiek, ga met de muis op de **rode stip bij 1766 cm⁻¹** staan (het gele vakje verschijnt)
   en klik. Onder de grafiek verschijnt de tabel: *Volgens de regels: Ester (–COO–): C=O-rek* en een lijst met
   mogelijke bindingen. Vertel: *"De tabel zegt 'mogelijke' bindingen, omdat de gebieden in de correlatietabel
   overlappen. Onder 1500 cm⁻¹ zegt hij er eerlijk bij dat het vingerafdrukgebied is."*
4. Scrol naar **functionele groepen**: *Ester (–COO–), zekerheid hoog: C=O-rek bij 1766 cm⁻¹, C–O–C-rek bij
   1242 cm⁻¹*. Vertel: *"Dit zijn vaste ALS-DAN-regels uit de correlatietabel. Er is niets getraind; je kunt elke
   stap narekenen. 1766 is hoger dan de 1740 uit het studieboek, omdat dit een gasfasespectrum is."*

## 2:40 – 3:50 · Waar het fout gaat (eerlijk zijn)

Laat "Eerlijke test" **aan** staan.

1. **Upload `1-hexeen_gas_C592416_IR_0.jdx`.** Nummer 1 is **1-Pentene (92,6%)**, niet 1-hexeen; 1-hexeen staat zelfs
   niet in de top 5. De app geeft wel de waarschuwing *"nummers 1 en 2 liggen heel dicht bij elkaar"*.
   Vertel: *"Dit is een homologe reeks: 1-penteen en 1-hexeen verschillen één CH₂-groep. Hun IR-spectra zijn bijna
   gelijk. IR kan dit gewoon slecht onderscheiden; daar heb je bijvoorbeeld GC-MS of het kookpunt voor nodig."*
   De functionele groep **C=C (alkeen)** wordt wél goed gevonden: de uitleglaag klopt, alleen de exacte stof niet.
2. **Upload `butylamine_vloeistof_C109739_IR_2.jdx`.** Nummer 1 is **1,5-Pentanediamine (80,5%)**; butylamine staat
   niet in de top 5, en **de app geeft géén waarschuwing**.
   Vertel: *"Dit is het gevaarlijkste soort fout: een redelijk hoge score, geen waarschuwing, en toch fout. Daarom
   blijft vakkennis nodig."* Dit sluit aan op LU3. Ook hier klopt de uitleglaag wel: **N–H (amine), zekerheid
   middel** (N–H-rek bij 3298 cm⁻¹, N–H-buiging bij 1602 cm⁻¹).

De functionele groepen die in deze demo genoemd worden staan ook in `docs/demo_eerlijke_test.txt` (regels "GROEP").

## 3:50 – 4:30 · Hoe goed is het in cijfers?

Laat [`evaluatie.md`](evaluatie.md) zien (of een dia met de tabel):

- Leave-one-out op 3.934 spectra van 1.735 stoffen: **top-1 ≈ 53%, top-5 ≈ 70%** (cosinus).
- Met een referentie in dezelfde fase ligt top-1 veel hoger dan wanneer de stof alleen in een andere fase is gemeten.
- Op de tien voorbeeldbestanden (eerlijke test): 5 van 10 op plek 1, 7 van 10 in de top 5.
- Zoeken door de hele bibliotheek: enkele tientallen milliseconden.

## 4:30 – 5:00 · Afsluiting

> "De app versnelt het zoeken en laat zien waarom hij iets denkt, maar hij herkent alleen stoffen die in de database
> staan, mengsels niet, en hij is gebouwd op vooral gasfasespectra. Hij vervangt de laborant niet; hij geeft een
> onderbouwde shortlist."

---

### Als er iets misgaat tijdens de demo

| Probleem | Oplossing |
|---|---|
| Browser opent niet | Typ zelf <http://localhost:8501> |
| "Referentiebibliotheek ontbreekt" | `setup.bat` is niet (helemaal) gedraaid; laat dan alleen de grafiek en de functionele groepen zien |
| Uploaden lukt niet | Kies hetzelfde bestand in de keuzelijst "voorbeeldspectrum" |
