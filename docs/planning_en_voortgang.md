# Planning en voortgang

Hoort bij **LU5** (zelfstandig en zelfsturend werken). Projectdag: maandag 16 november 2026.

> **[CONCEPT – zelf nalezen en aanvullen]** De planning en de beslissingen zijn vastgelegd door de AI-assistent.
> Vul aan met je eigen ervaring van de dag (wat deed jij op welk moment, wat vond je lastig).

## 1. Dagplanning per user story

De opdracht vroeg om eerst een planning te maken en dan direct te beginnen. De planning is in deze volgorde gemaakt,
omdat elke stap de vorige nodig heeft:

| # | Onderdeel | User story | Waarom op deze plek |
|---|---|---|---|
| 1 | Omgeving, git, virtual environment | – | Basis voor alles |
| 2 | Database downloaden en bibliotheek bouwen | – (Database) | Zonder data geen onderzoek, tests of evaluatie; grootste risico, dus eerst |
| 3 | Onderzoek JCAMP-DX-bibliotheken | RS | Bepaalt hoe bestanden ingelezen worden |
| 4 | Validatie, inlezen, upload en grafiek | US | De eerste zichtbare functie van de app |
| 5 | Piekdetectie, matching, notebook, theorie | LS | Kern van de herkenning |
| 6 | Evaluatie, keuze van de methode | Matching en evaluatie | Nodig voor onderbouwde keuzes in de app |
| 7 | Functionele groepen, app afmaken | Uitleglaag | Bouwt voort op piekdetectie |
| 8 | Tests, controle in de browser | Alle | Kwaliteitscriteria aantonen |
| 9 | Documentatie leeruitkomsten, checklist | LU1–LU5 | Pas zinvol als er echte meetresultaten zijn |
| 10 | `setup.bat` op een schone kopie testen, eindcontrole | Definition of done | Als laatste, op de definitieve versie |

## 2. Hoe het werkelijk liep

In de praktijk liepen stappen 3–7 door elkaar: de JCAMP-parser was nodig om de database te bouwen (stap 2), en de
evaluatie (stap 6) leidde tot een verbetering van de voorbewerking die weer in de app terechtkwam. Het onderzoek naar
bibliotheken (RS) is daardoor **na** het schrijven van de eigen parser gedaan; het bevestigde die keuze achteraf met
metingen in plaats van haar vooraf te bepalen.

Commit-tijden uit de git-geschiedenis (`git log`):

| Tijd | Commit |
|---|---|
| 12:30 | Projectopzet en database: download- en bouwscript |
| 12:39 | LS (deel 1): piekdetectie en spectra-matching met tests |
| 12:39 | Functionele groepen: expertsysteem met 8 regels |
| 12:39 | US: IR-spectrum uploaden, valideren en tonen |
| 12:39 | Matching: evaluatie en keuze van methode en voorbewerking |
| 13:06 | RS: onderzoek JCAMP-DX-bibliotheken |
| 13:06 | Functionele groepen: regeltoets opnieuw gedraaid |
| 13:15 | LS (deel 2): notebook en theorie-document |
| 13:15 | Evaluatie: eerlijkere beschrijving; eerlijke test op voorbeeldbestanden |
| 13:15 | start.bat: headless, browser openen |
| later | Documentatie leeruitkomsten, testresultaten, checklist (zie `git log`) |

**Eerlijke kanttekening:** de opdracht vroeg om na elke afgeronde user story te committen. De eerste vier stories zijn
pas samen gecommit (om 12:39, in vier aparte commits) toen ze alle vier werkten, niet elk direct na afronding. Vanaf
het RS-onderzoek is wel na elke story gecommit. (De tijden zijn die van de computer; de dag begon eerder met het
downloaden en inventariseren van de database.)

## 3. Wat is af, wat niet?

| Onderdeel | Status |
|---|---|
| Database downloaden (script) en bibliotheek bouwen | ✅ af (18.998 spectra) |
| US – uploaden, valideren, grafiek | ✅ af |
| RS – onderzoek bibliotheken | ✅ af |
| LS – piekdetectie, notebook, theorie, tests | ✅ af |
| Matching + evaluatie | ✅ af (top-1 52,9%, top-5 69,5%) |
| Functionele groepen | ✅ af (8 regels, getoetst) |
| Documentatie LU1–LU5 | ✅ concepten af; **zelfevaluatie en reflectie nog door de student** |
| `setup.bat` / `start.bat` | ✅ getest op een schone kopie (zie `docs/testresultaten.md`) |
| Python 3.10 ondersteunen | ❌ niet gehaald: de app vraagt Python 3.12+ (zie `docs/criteria_checklist.md`) |
| Test op een echte tablet | ❌ niet gedaan; alleen tabletformaat geëmuleerd in een browser |

## 4. Beslissingen onderweg

| Beslissing | Door wie | Waarom |
|---|---|---|
| Database uit een oude fork halen, nadat de oorspronkelijke repository de data had verwijderd | **Student** (AI stopte en vroeg het, zoals afgesproken) | Volledige database nodig voor een zinvolle evaluatie; ethische afweging in `docs/ethiek_en_verantwoord_gebruik.md` |
| Eigen JCAMP-parser in plaats van een bibliotheek | AI | Strenge validatie en Nederlandse foutmeldingen; onderbouwd in het RS-onderzoek |
| Python 3.14 en de nieuwste pakketversies | AI | Op deze computer beschikbaar; gevolg: Python 3.10 wordt niet ondersteund |
| Duplicaatregel uitbreiden met de QUANT-IR-reeks | AI | Anders is de evaluatie te rooskleurig |
| Voorbewerking "logaritme + afgeleide" | AI | Top-1 van ± 31% naar ± 53% (gemeten) |
| Cosinus als standaardmethode | AI | Even goed als Pearson, eenvoudiger en sneller |
| Waarschuwingsdrempels 65% en 5 procentpunt | AI | Gekozen op basis van de gemeten scoreverdelingen |
| Schakelaar "Eerlijke test" in de app | AI | Voorbeeldbestanden zouden anders altijd 100% scoren |

## 5. Mogelijke vervolgstappen (met meer tijd)

- Testen met eigen metingen (ATR) van het lab, en kijken hoeveel slechter de herkenning dan is.
- Een filter op fase in de app ("zoek alleen in vloeistofspectra").
- Mengselanalyse: het spectrum proberen te verklaren als som van twee referenties.
- De app aanpassen zodat hij ook met Python 3.10 werkt (oudere numpy/scipy vastzetten en opnieuw testen).
- Eigen referentiespectra kunnen toevoegen aan de bibliotheek.

## Richtvragen (zelf aanvullen)

- Hoe verliep jouw dag vergeleken met deze planning?
- Op welk moment moest je een beslissing nemen, en hoe voelde dat?
- Wat zou je de volgende keer anders plannen?
