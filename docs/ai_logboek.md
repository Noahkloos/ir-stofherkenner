# AI-logboek

Hoort bij **LU4** (AI-tools en -technieken gebruiken). Dit logboek is tijdens het werk bijgehouden door de
AI-assistent (Claude Code). Het beschrijft welke stappen de AI deed, welke problemen er waren en hoe die zijn opgelost,
en welke keuzes er gemaakt zijn (en door wie).

**Gebruikte AI-tool:** Claude Code (desktop-app, Windows), eerst met het model Claude Fable 5.2 en na een onderbreking
door een gebruikslimiet met Claude Opus 5.5, met Claude Fable 5.2 als "advisor" (een tweede model dat het werk
tussentijds kritisch nakeek). De student schreef zelf geen code; de AI schreef alle code, tests en concepten van de
documentatie.

## 1. Welke AI-technieken zitten er in de app (en waarom geen machine learning)?

| Techniek | Soort AI | Waar |
|---|---|---|
| Piekdetectie (Savitzky-Golay, MAD-ruisschatting, prominentie, breedte) | Klassieke signaalverwerking: vaste, uitlegbare rekenregels | `stofherkenner/piekdetectie.py` |
| Functionele groepen herkennen | **Symbolische AI / expertsysteem**: kennis van een expert (de correlatietabel) vastgelegd als ALS-DAN-regels, plus "meta-regels" die conclusies tegen elkaar afwegen | `stofherkenner/functionele_groepen.py` |
| Stof zoeken | **Similarity search** (nearest-neighbour zoeken): het spectrum is een vector, de bibliotheek wordt doorzocht op de meest gelijkende vector (cosinusgelijkenis) | `stofherkenner/matching.py` |

**Waarom geen machine learning?**

1. **De vraag past bij zoeken, niet bij leren.** "Welke stof is dit?" met een bibliotheek van referentiespectra is
   precies het probleem dat een zoekactie op gelijkenis oplost.
2. **Te weinig voorbeelden per stof.** Van de 15.817 stoffen hebben er maar 1.735 meer dan één (echt verschillend)
   spectrum. Een classifier die 15.817 klassen moet leren met meestal één voorbeeld per klasse werkt niet.
3. **Uitlegbaarheid.** Elke uitkomst is terug te voeren op "lijkt op dit referentiespectrum" en "piek bij 1742 cm⁻¹".
   Dat is belangrijk in een lab, waar een uitslag verantwoord moet kunnen worden (zie LU3).
4. **Uitbreidbaar zonder trainen.** Een nieuwe stof toevoegen = een spectrum aan de bibliotheek toevoegen.
5. **Haalbaar in één dag** en controleerbaar met tests.

Er is wel iets "afgesteld" (de voorbewerking, de drempels van de waarschuwingen), maar dat zijn een handvol
instellingen die met de hand gekozen zijn op basis van metingen, geen model met geleerde gewichten.

## 2. Logboek: stappen, problemen en oplossingen

| # | Wat deed de AI? | Probleem / bevinding | Oplossing / keuze | Wie besliste? |
|---|---|---|---|---|
| 1 | Omgeving gecontroleerd | Standaard-Python is Anaconda 3.9 (te oud); Python 3.14 is via `py` beschikbaar | Virtual environment met Python 3.14 | AI |
| 2 | NistChemData-repository onderzocht via de GitHub-API | De repository is verhuisd (nu `muCommons/NistChemData`) en de auteur heeft in mei 2026 **alle databestanden verwijderd**, ook uit de geschiedenis, om NIST-data niet te herverspreiden | **Gestopt en de student gevraagd** (zoals de opdracht voorschreef). Opties voorgelegd: kleine set via NIST zelf ophalen, oude kopie zoeken, of andere database | **Student**: "oude kopie zoeken" |
| 3 | Forks doorzocht | Twee forks hebben nog de Git-LFS-verwijzing naar `nist_IR.zip` (202.550.662 bytes) en het bestand is nog te downloaden | `download_database.py` haalt het daar op en controleert het **SHA-256-controlegetal** uit de LFS-verwijzing; veilig uitpakken (beveiliging tegen "zip slip" en zip-bommen) | AI |
| 4 | Alle 19.582 bestanden geïnventariseerd | Vijf soorten y-eenheden (transmissie, absorbantie, QUANT-IR-absorptiecoëfficiënt, reflectie, "dispersion index"), x in 1/CM, cm-1 én MICROMETERS, 352 bestanden zonder meetpunten, 124 bestanden met meerdere spectra | Parser en voorbewerking hierop ingericht; reflectie e.d. worden overgeslagen en gelogd | AI |
| 5 | Bibliotheek gebouwd | 18.998 spectra, 584 overgeslagen (met reden in `data/overgeslagen.csv`) | – | AI |
| 6 | Duplicaten onderzocht | Eerste regel (cosinus ≥ 0,99) miste een deel van de NIST-reeks QUANT-IR: dezelfde gasmeting bij 5 resoluties en enkele concentraties | Tweede regel toegevoegd: spectra uit dezelfde QUANT-IR-reeks van dezelfde stof zijn altijd duplicaten (982 gemarkeerd) | AI |
| 7 | Eerste evaluatie gedraaid | Teleurstellend: top-1 cosinus 30,6%, Pearson 31,8%, Euclidisch 25,1% | Analyse: 85% van de fouten had alleen een referentie in een andere fase; de hoogste piek domineert de score | AI |
| 8 | **Verkenning op de hele testset**: wortel, basislijncorrectie, afgeleide | "Afgeleide van de wortel" gaf 46,1% top-1 | Idee: compressie + afgeleide. **Let op:** deze verkenning gebruikte álle testdata | AI |
| 9 | Stoffen in twee vaste helften verdeeld; details alleen op de afstelhelft gekozen | log(1+100·A) + afgeleide (venster 9): 54,0% op de afstelhelft, 51,9% op de controlehelft | Gekozen. In de rapporten staat eerlijk dat de controlehelft door stap 8 niet helemaal onafhankelijk is (aangescherpt na kritiek van de advisor) | AI |
| 10 | Methode gekozen | Cosinus en Pearson daarna even goed (52,9%) | Cosinus: zelfde nauwkeurigheid, eenvoudiger en sneller | AI, onderbouwd in `docs/theorie_matching.md` |
| 11 | Functionele-groepenregels geschreven en uitgeprobeerd | Fouten gevonden: aceton gaf "ester (hoog)", butylamine gaf "aromaat" | Ester-regel eist nu dat de C–O–C-band ≥ 70% van de C=O is; aromaat-regel eist scherpe pieken; extra meta-regels | AI |
| 12 | Regels getoetst op de hele bibliotheek | Geen lijst "welke stof heeft welke groep" beschikbaar | Toets via de naam (trefkans) en de molecuulformule (zeker vals alarm); zie `docs/controle_functionele_groepen.md` | AI |
| 13 | Waarschuwingsdrempels gekozen | Eerste drempels (60% / 3 punten) vingen te weinig fouten | Op basis van de scoreverdelingen: 65% / 5 punten (78% van de foute antwoorden krijgt een waarschuwing, 21% van de goede ook) | AI |
| 14 | Tests geschreven (170) | Test "losse uitschieter is geen piek" faalde: gladmaken smeert een spike uit tot iets dat op een smalle piek lijkt | Breedte wordt nu gemeten in het **ruwe** spectrum | AI |
| 15 | Bibliotheekonderzoek | API-naam van `jcamp` verschilt per versie (`jcamp_readfile` / `readfile`); `chemparse` blijkt een formule-parser | Beide namen ondersteund; chemparse als correctie in het onderzoek vermeld | AI |
| 16 | Windows-specifieke problemen | Console (cp1252) kan tekens als cm⁻¹ en ≡ niet tonen → scripts crashten bij het printen | Alle scripts zetten de uitvoer op UTF-8 | AI |
| 17 | App in de browser gecontroleerd | Desktop (1366×900) en tablet (768×1024) geëmuleerd in de ingebouwde browser van de AI-tool | Geen horizontaal scrollen, grafieken passen binnen het scherm. Niet getest op een echte tablet | AI |
| 18 | Advisor-review | Streamlit vraagt bij de allereerste start om een e-mailadres als `headless` uit staat; dat zou een dubbelklik op `start.bat` laten "hangen" | `headless = true`; `start.bat` opent zelf de browser | AI (op advies van de advisor) |
| 19 | Notebook uitvoeren | In de omgeving van de AI kon een Jupyter-kernel geen verbinding maken via localhost (de kernel start wel, maar reageert niet) | Codecellen uitgevoerd in één Python-proces met `scripts/voer_notebook_uit.py`; de uitvoer en grafieken zijn echt. Op een gewone laptop werkt Jupyter normaal | AI |
| 20 | Notebook nagekeken | Een paar conclusies stonden vast in de tekst ("duidelijke kloof", "afstand wordt groter") | Vervangen door zinnen die uit de echte uitvoer berekend worden | AI (op advies van de advisor) |
| 21 | Eerlijke test op de 10 voorbeeldbestanden | Voorbeeldbestanden staan zelf in de bibliotheek (100%) | Schakelaar "Eerlijke test" in de app; demo-voorbeelden van fouten (1-hexeen, butylamine) komen uit deze echte run | AI |
| 22 | `setup.bat` getest op een schone kopie van de repository | In de omgeving van de AI vond `cmd` een batchbestand niet via een relatieve naam | Aangeroepen met het volledige pad; `setup.bat` gaat zelf naar zijn eigen map. Resultaat: exitcode 0 na 364 s, daarna 169 tests geslaagd in de kopie (zie `docs/testresultaten.md`) | AI |
| 22b | `start.bat` getest | Eerste "geslaagde" test bleek een vals positief: poort 8501 werd nog bezet door een eerder gestarte testserver. Die mocht de AI niet stoppen (toestemming geweigerd) | Het startcommando van de schone kopie apart getest op poort 8502 (met tijdslimiet); `start.bat` zelf op 8501 niet volledig getest. Eerlijk vermeld in de checklist | AI |
| 23 | Sessie onderbroken door een gebruikslimiet | – | Verder gewerkt met een ander model; geen werk verloren doordat er na elke user story gecommit werd | – |

## 3. Wat ging goed en wat minder goed in de samenwerking met AI? (zelf aanvullen)

*[Aanvullen door de student. Richtvragen:]*

- Op welk moment had je zelf moeten (of willen) ingrijpen? Waar vertrouwde je de AI misschien te snel?
- De AI stopte bij de database-blokkade en liet jou kiezen. Hoe beoordeel je die keuze nu?
- De advisor vond fouten die de eerste AI niet zag (bijv. de niet volledig onafhankelijke controlehelft). Wat zegt dat
  over het controleren van AI-werk?
- Hoe heb je gecontroleerd dat de cijfers in de documentatie echt uit een run komen?
- Welke onderdelen kun je nu zelf uitleggen, en welke nog niet?
