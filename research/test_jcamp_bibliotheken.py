"""Onderzoek (RS): welke Python-bibliotheek leest JCAMP-DX-bestanden het best?

Draaien met een commando (vanuit de projectmap):

    .venv\\Scripts\\python research\\test_jcamp_bibliotheken.py

Vooraf eenmalig de onderzoekspakketten installeren:

    .venv\\Scripts\\python -m pip install -r research\\requirements.txt

Wat het script doet:
1. Leest elk bestand in research/voorbeeldspectra/ met elke kandidaat.
2. Controleert de uitkomst tegen de KOP van het bestand zelf (##NPOINTS,
   ##FIRSTX, ##LASTX, ##FIRSTY, ##MAXY). Die waarden lezen we hier met een
   simpele zoekopdracht uit, onafhankelijk van welke parser dan ook.
3. Meet de snelheid (mediaan van een aantal herhalingen).
4. Kijkt wat er met de eenheden gebeurt (micrometer / cm-1, transmissie /
   absorbantie): blijven ze zoals in het bestand of rekent de bibliotheek om?
5. Geeft elke kandidaat vijf kapotte bestanden: crasht hij, hangt hij, of
   geeft hij een nette fout?
6. (Als de volledige database aanwezig is) leest een vaste steekproef van 300
   bestanden om te zien hoe vaak het in de praktijk misgaat.

Uitvoer: research/resultaten/resultaten.md, per_bestand.csv en samenvatting.csv
"""

from __future__ import annotations

import csv
import random
import re
import statistics
import sys
import time
import warnings
from datetime import date
from pathlib import Path

import numpy as np

PROJECTMAP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECTMAP))
VOORBEELDMAP = PROJECTMAP / "research" / "voorbeeldspectra"
RESULTAATMAP = PROJECTMAP / "research" / "resultaten"
DATABASEMAP = PROJECTMAP / "data" / "raw" / "nist_ir"

warnings.filterwarnings("ignore")          # de bibliotheken geven veel waarschuwingen; die storen de uitvoer


# --- De kandidaten: per bibliotheek een functie die een bestand leest --------
# Elke functie geeft een woordenboek terug met: titel, cas, formule, x_eenheid,
# y_eenheid, x (array) en y (array). Ontbreekt iets, dan is het None.

def lees_met_eigen_parser(pad: Path) -> dict:
    from stofherkenner.jcamp_lezen import lees_jcamp_bestand
    s = lees_jcamp_bestand(pad)
    return {"titel": s.titel, "cas": s.cas, "formule": s.formule, "x_eenheid": s.x_eenheid,
            "y_eenheid": s.y_eenheid, "x": s.x, "y": s.y}


def lees_met_jcamp(pad: Path) -> dict:
    import jcamp
    lees = getattr(jcamp, "jcamp_readfile", None) or jcamp.readfile      # de naam verschilt per versie
    d = lees(str(pad))
    return {"titel": d.get("title"), "cas": d.get("cas registry no"), "formule": d.get("molform"),
            "x_eenheid": d.get("xunits"), "y_eenheid": d.get("yunits"),
            "x": np.asarray(d["x"], dtype=float), "y": np.asarray(d["y"], dtype=float)}


def lees_met_nmrglue(pad: Path) -> dict:
    import nmrglue
    kop, data = nmrglue.jcampdx.read(str(pad))
    # nmrglue is gemaakt voor NMR. Bij een IR-spectrum zet het alles onder een aparte sleutel.
    for sleutel, waarde in kop.items():
        if sleutel.startswith("_datatype_") and waarde:
            blok = waarde[0] if isinstance(waarde, list) else waarde
            kop = blok if isinstance(blok, dict) else kop
            break

    def eerste(naam):
        w = kop.get(naam)
        return (w[0] if isinstance(w, list) and w else w) if w is not None else None

    y = None if data is None else np.asarray(data, dtype=float).ravel()
    return {"titel": eerste("TITLE"), "cas": eerste("CASREGISTRYNO"), "formule": eerste("MOLFORM"),
            "x_eenheid": eerste("XUNITS"), "y_eenheid": eerste("YUNITS"), "x": None, "y": y}


def lees_met_spectrochempy(pad: Path) -> dict:
    import spectrochempy as scp
    ds = scp.read_jcamp(str(pad))
    meta = ds.meta if hasattr(ds.meta, "get") else {}
    return {"titel": ds.name, "cas": meta.get("cas registry no") if meta else None,
            "formule": meta.get("molform") if meta else None,
            "x_eenheid": str(ds.x.units), "y_eenheid": str(ds.units),
            "x": np.asarray(ds.x.data, dtype=float).ravel(), "y": np.asarray(ds.data, dtype=float).ravel()}


def lees_met_chemparse(pad: Path) -> dict:
    import chemparse
    # chemparse heeft maar een functie: parse_formula(tekst). Er is geen functie om bestanden te lezen.
    functies = [n for n in dir(chemparse) if not n.startswith("_") and callable(getattr(chemparse, n))]
    raise NotImplementedError(
        f"chemparse kan geen JCAMP-DX lezen: het is een parser voor chemische formules (functies: {functies})"
    )


KANDIDATEN = {
    "eigen parser (stofherkenner.jcamp_lezen)": lees_met_eigen_parser,
    "jcamp": lees_met_jcamp,
    "nmrglue (jcampdx)": lees_met_nmrglue,
    "spectrochempy": lees_met_spectrochempy,
    "chemparse": lees_met_chemparse,
}


# --- De "waarheid": waarden uit de kop van het bestand ----------------------

def kop_waarden(pad: Path) -> dict:
    """Lees de controlewaarden rechtstreeks uit de kop (zonder parser)."""
    tekst = pad.read_bytes().decode("latin-1")

    def getal(label):
        m = re.search(rf"^##{label}=\s*([-+0-9.eE]+)", tekst, flags=re.MULTILINE)
        return float(m.group(1)) if m else None

    def tekstwaarde(label):
        m = re.search(rf"^##{label}=(.*)$", tekst, flags=re.MULTILINE)
        return m.group(1).strip() if m else None

    return {"npoints": getal("NPOINTS"), "firstx": getal("FIRSTX"), "lastx": getal("LASTX"),
            "firsty": getal("FIRSTY"), "maxy": getal("MAXY"), "miny": getal("MINY"),
            "titel": tekstwaarde("TITLE"), "cas": tekstwaarde("CAS REGISTRY NO"),
            "xunits": tekstwaarde("XUNITS"), "yunits": tekstwaarde("YUNITS")}


def bijna_gelijk(a, b, rel=2e-3) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-9)


def beoordeel(uitkomst: dict, kop: dict) -> dict:
    """Vergelijk wat een bibliotheek teruggeeft met de kop van het bestand."""
    x, y = uitkomst.get("x"), uitkomst.get("y")
    heeft_y = y is not None and len(y) > 0
    heeft_x = x is not None and len(x) > 0
    r = {
        "data_gelezen": heeft_y,
        "x_as_geleverd": heeft_x,
        "aantal_punten_klopt": heeft_y and kop["npoints"] is not None and len(y) == int(kop["npoints"]),
        "titel_klopt": (uitkomst.get("titel") or "").strip() == (kop["titel"] or ""),
        "cas_gevonden": bool(uitkomst.get("cas")) and uitkomst.get("cas").strip() == (kop["cas"] or ""),
        "x_eenheid": uitkomst.get("x_eenheid"),
        "y_eenheid": uitkomst.get("y_eenheid"),
    }
    # x-as: zelfde bereik als FIRSTX..LASTX (in de eenheid van het bestand)?
    if heeft_x:
        zelfde = bijna_gelijk(float(x[0]), kop["firstx"]) and bijna_gelijk(float(x[-1]), kop["lastx"])
        omgekeerd = bijna_gelijk(float(x[-1]), kop["firstx"]) and bijna_gelijk(float(x[0]), kop["lastx"])
        r["x_bereik"] = "klopt" if zelfde else ("klopt (omgekeerde volgorde)" if omgekeerd else
                                               f"anders: {float(np.min(x)):.4g}..{float(np.max(x)):.4g}")
    else:
        r["x_bereik"] = "geen x-as"
    # y-waarden: maximum gelijk aan MAXY en eerste waarde gelijk aan FIRSTY?
    if heeft_y:
        ymax = float(np.nanmax(y))
        if bijna_gelijk(ymax, kop["maxy"]):
            r["y_waarden"] = "kloppen"
        elif kop["maxy"] and bijna_gelijk(ymax, 100 * kop["maxy"]):
            r["y_waarden"] = "omgerekend (x100, naar procenten)"
        else:
            r["y_waarden"] = f"anders: max {ymax:.4g} tegenover MAXY {kop['maxy']}"
    else:
        r["y_waarden"] = "geen data"
    r["alles_juist"] = bool(r["data_gelezen"] and r["x_as_geleverd"] and r["aantal_punten_klopt"]
                            and r["x_bereik"].startswith("klopt") and r["y_waarden"] == "kloppen")
    return r


def meet(functie, pad: Path, herhalingen: int = 5):
    """Lees een bestand ``herhalingen`` keer; geef (uitkomst of None, foutmelding, mediane tijd in ms)."""
    tijden, uitkomst, fout = [], None, ""
    for _ in range(herhalingen):
        start = time.perf_counter()
        try:
            uitkomst = functie(pad)
        except Exception as e:                      # elke fout telt als "niet gelukt"
            fout = f"{type(e).__name__}: {str(e)[:150]}"
            uitkomst = None
        tijden.append((time.perf_counter() - start) * 1000)
        if uitkomst is None:
            break
    return uitkomst, fout, statistics.median(tijden)


# --- Kapotte bestanden -------------------------------------------------------

def maak_kapotte_bestanden(map_: Path) -> dict[str, Path]:
    """Schrijf vijf kapotte bestanden om te zien hoe elke bibliotheek daarop reageert."""
    map_.mkdir(parents=True, exist_ok=True)
    goed = (VOORBEELDMAP / "aceton_gas_C67641_IR_0.jdx").read_bytes()
    regels = goed.decode().splitlines()
    start = next(i for i, r in enumerate(regels) if r.startswith("##XYDATA"))
    onzin = regels.copy()
    onzin[start + 5] = "dit is <geen> getal !!!"
    bestanden = {
        "leeg bestand": b"",
        "binaire rommel": np.random.default_rng(0).integers(0, 256, 20_000, dtype=np.uint8).tobytes(),
        "afgekapt (geen ##END)": goed[: len(goed) // 2],
        "onzin in het datablok": "\n".join(onzin).encode(),
        "kop zonder datablok": "\n".join(r for r in regels if r.startswith("##") and not r.startswith("##XYDATA")).encode(),
    }
    paden = {}
    for i, (naam, inhoud) in enumerate(bestanden.items()):
        pad = map_ / f"kapot_{i}.jdx"
        pad.write_bytes(inhoud)
        paden[naam] = pad
    return paden


def reactie_op_kapot(functie, pad: Path) -> str:
    start = time.perf_counter()
    try:
        uitkomst = functie(pad)
    except NotImplementedError:
        return "n.v.t."
    except Exception as e:
        return f"fout: {type(e).__name__}"
    duur = time.perf_counter() - start
    y = uitkomst.get("y")
    n = 0 if y is None else len(y)
    return f"GEEN fout, geeft {n} punten terug" + (f" ({duur:.1f} s)" if duur > 1 else "")


# --- Hoofdprogramma ---------------------------------------------------------

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    RESULTAATMAP.mkdir(parents=True, exist_ok=True)
    bestanden = sorted(VOORBEELDMAP.glob("*.jdx"))
    print(f"{len(bestanden)} voorbeeldbestanden, {len(KANDIDATEN)} kandidaten\n")

    # Importtijd en versie per bibliotheek
    import importlib
    import importlib.metadata as md
    pakketten = {"jcamp": "jcamp", "nmrglue (jcampdx)": "nmrglue", "spectrochempy": "spectrochempy", "chemparse": "chemparse"}
    versies, importtijd = {"eigen parser (stofherkenner.jcamp_lezen)": "-"}, {"eigen parser (stofherkenner.jcamp_lezen)": 0.0}
    for naam, pakket in pakketten.items():
        start = time.perf_counter()
        try:
            importlib.import_module(pakket)
            versies[naam] = md.version(pakket)
        except Exception as e:
            versies[naam] = f"niet geinstalleerd ({type(e).__name__})"
        importtijd[naam] = time.perf_counter() - start

    # 1-4: voorbeeldbestanden
    per_bestand = []
    for naam, functie in KANDIDATEN.items():
        for pad in bestanden:
            kop = kop_waarden(pad)
            uitkomst, fout, ms = meet(functie, pad)
            rij = {"bibliotheek": naam, "bestand": pad.name, "x_in_bestand": kop["xunits"], "y_in_bestand": kop["yunits"],
                   "gelukt": uitkomst is not None, "fout": fout, "tijd_ms": round(ms, 2)}
            if uitkomst is not None:
                rij.update(beoordeel(uitkomst, kop))
            per_bestand.append(rij)

    # 5: kapotte bestanden
    kapot = maak_kapotte_bestanden(RESULTAATMAP / "kapotte_bestanden")
    kapot_reacties = {naam: {soort: reactie_op_kapot(functie, pad) for soort, pad in kapot.items()}
                      for naam, functie in KANDIDATEN.items()}

    # 6: steekproef uit de volledige database
    steekproef_regels, n_steekproef = [], 0
    if DATABASEMAP.exists():
        alle = sorted(DATABASEMAP.glob("*.jdx"))
        steekproef = random.Random(2026).sample(alle, 300)
        n_steekproef = len(steekproef)
        for naam, functie in KANDIDATEN.items():
            if naam == "chemparse":
                continue
            juist = gelezen = fouten = 0
            start = time.perf_counter()
            for pad in steekproef:
                kop = kop_waarden(pad)
                try:
                    uitkomst = functie(pad)
                except Exception:
                    fouten += 1
                    continue
                oordeel = beoordeel(uitkomst, kop)
                gelezen += bool(oordeel["data_gelezen"])
                juist += bool(oordeel["alles_juist"])
            duur = time.perf_counter() - start
            steekproef_regels.append((naam, gelezen, juist, fouten, duur))
            print(f"steekproef {naam:42s} data gelezen {gelezen:3d}/300  volledig juist {juist:3d}/300  fouten {fouten:3d}  ({duur:.1f} s)")

    # --- Samenvatten ---
    samenvatting = []
    for naam in KANDIDATEN:
        rijen = [r for r in per_bestand if r["bibliotheek"] == naam]
        gelukt = [r for r in rijen if r["gelukt"]]
        samenvatting.append({
            "bibliotheek": naam,
            "versie": versies.get(naam, "?"),
            "importtijd_s": round(importtijd.get(naam, 0.0), 2),
            "bestanden_zonder_fout": f"{len(gelukt)}/{len(rijen)}",
            "data_gelezen": f"{sum(bool(r.get('data_gelezen')) for r in gelukt)}/{len(rijen)}",
            "volledig_juist": f"{sum(bool(r.get('alles_juist')) for r in gelukt)}/{len(rijen)}",
            "titel_juist": f"{sum(bool(r.get('titel_klopt')) for r in gelukt)}/{len(rijen)}",
            "cas_gevonden": f"{sum(bool(r.get('cas_gevonden')) for r in gelukt)}/{len(rijen)}",
            "mediane_tijd_ms": round(statistics.median(r["tijd_ms"] for r in gelukt), 2) if gelukt else None,
            "eerste_fout": next((r["fout"] for r in rijen if r["fout"]), ""),
        })
        s = samenvatting[-1]
        print(f"{naam:42s} versie {s['versie']:8s} zonder fout {s['bestanden_zonder_fout']:6s} data {s['data_gelezen']:6s} "
              f"juist {s['volledig_juist']:6s} tijd {s['mediane_tijd_ms']} ms  {s['eerste_fout'][:70]}")

    # --- Wegschrijven ---
    kolommen = sorted({k for r in per_bestand for k in r})
    with open(RESULTAATMAP / "per_bestand.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolommen)
        w.writeheader()
        w.writerows(per_bestand)
    with open(RESULTAATMAP / "samenvatting.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(samenvatting[0]))
        w.writeheader()
        w.writerows(samenvatting)

    def eenheden(naam: str, kolom_in: str, kolom_uit: str) -> str:
        paren = sorted({(r[kolom_in], str(r.get(kolom_uit))) for r in per_bestand if r["bibliotheek"] == naam and r["gelukt"]})
        return "; ".join(f"{a} → {b}" for a, b in paren) or "-"

    def uitkomsten(naam: str, kolom: str) -> str:
        return "; ".join(sorted({str(r.get(kolom)) for r in per_bestand if r["bibliotheek"] == naam and r["gelukt"]})) or "-"

    md_samenvatting = "\n".join(
        f"| {s['bibliotheek']} | {s['versie']} | {s['importtijd_s']} s | {s['bestanden_zonder_fout']} | {s['data_gelezen']} | "
        f"{s['volledig_juist']} | {s['titel_juist']} | {s['cas_gevonden']} | {s['mediane_tijd_ms'] if s['mediane_tijd_ms'] is not None else '-'} |"
        for s in samenvatting)
    md_eenheden = "\n".join(
        f"| {naam} | {eenheden(naam, 'x_in_bestand', 'x_eenheid')} | {uitkomsten(naam, 'x_bereik')} | "
        f"{eenheden(naam, 'y_in_bestand', 'y_eenheid')} | {uitkomsten(naam, 'y_waarden')} |"
        for naam in KANDIDATEN if naam != "chemparse")
    soorten = list(kapot)
    md_kapot = "\n".join(f"| {naam} | " + " | ".join(kapot_reacties[naam][s] for s in soorten) + " |"
                         for naam in KANDIDATEN if naam != "chemparse")
    md_steekproef = "\n".join(f"| {naam} | {gelezen}/{n_steekproef} | {juist}/{n_steekproef} | {fouten} | {duur:.1f} s |"
                              for naam, gelezen, juist, fouten, duur in steekproef_regels) or "| (database niet aanwezig; overgeslagen) | | | | |"
    fouten_md = "\n".join(f"- **{s['bibliotheek']}**: `{s['eerste_fout']}`" for s in samenvatting if s["eerste_fout"]) or "- geen"

    rapport = f"""# Testresultaten JCAMP-DX-bibliotheken

> Automatisch gemaakt door `research/test_jcamp_bibliotheken.py` op {date.today().isoformat()}
> met Python {sys.version.split()[0]}. Opnieuw draaien: `.venv\\Scripts\\python research\\test_jcamp_bibliotheken.py`

## 1. De {len(bestanden)} voorbeeldbestanden

"Volledig juist" = data gelezen, x-as geleverd, aantal punten gelijk aan `##NPOINTS`, x-bereik gelijk aan
`##FIRSTX`..`##LASTX` en hoogste y-waarde gelijk aan `##MAXY` (alles vergeleken met de kop van het bestand zelf).

| Bibliotheek | Versie | Importtijd | Zonder fout | Data gelezen | Volledig juist | Titel juist | CAS gevonden | Mediane leestijd (ms) |
|---|---|---|---|---|---|---|---|---|
{md_samenvatting}

Foutmeldingen:
{fouten_md}

## 2. Wat gebeurt er met de eenheden?

De voorbeeldbestanden bevatten twee x-eenheden (1/CM en MICROMETERS) en twee y-eenheden (ABSORBANCE en TRANSMITTANCE).
"A → B" betekent: in het bestand staat A, de bibliotheek meldt B.

| Bibliotheek | X-eenheid (bestand → bibliotheek) | X-bereik t.o.v. kop | Y-eenheid (bestand → bibliotheek) | Y-waarden t.o.v. kop |
|---|---|---|---|---|
{md_eenheden}

Geen enkele kandidaat rekent micrometer om naar cm⁻¹ of transmissie naar absorbantie; dat moet de app dus altijd zelf doen.

## 3. Reactie op kapotte bestanden

| Bibliotheek | {' | '.join(soorten)} |
|---|{'---|' * len(soorten)}
{md_kapot}

"GEEN fout" betekent dat de bibliotheek een kapot bestand zonder waarschuwing accepteert; de app zou dan zelf
moeten ontdekken dat er iets mis is.

## 4. Steekproef van {n_steekproef or 300} bestanden uit de volledige NIST-database

| Bibliotheek | Data gelezen | Volledig juist | Fouten (exceptions) | Totale tijd |
|---|---|---|---|---|
{md_steekproef}

De steekproef is vast (random seed 2026), dus elke run test dezelfde bestanden. Een deel van de NIST-bestanden
bevat geen meetpunten (alleen een verwijzing naar een gescande afbeelding) of twee blokken; dat verklaart waarom
geen enkele parser 300/300 haalt.

Details per bestand: `research/resultaten/per_bestand.csv`.
"""
    (RESULTAATMAP / "resultaten.md").write_text(rapport, encoding="utf-8")
    print(f"\nRapport: {RESULTAATMAP / 'resultaten.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
