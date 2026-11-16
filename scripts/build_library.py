"""Bouw de referentiebibliotheek uit de losse NIST JCAMP-DX-bestanden.

Gebruik:
    python scripts/build_library.py

Invoer : data/raw/nist_ir/*.jdx   (zie scripts/download_database.py)
Uitvoer: data/library.npz         (alle spectra op het vaste raster)
         data/metadata.csv        (naam, CAS, formule, fase, duplicaat-markering, ...)
         data/overgeslagen.csv    (welke bestanden zijn overgeslagen en waarom)
         data/build_log.txt       (samenvatting met aantallen)

Per bestand gebeurt precies hetzelfde als later met een geupload spectrum
(zie stofherkenner/voorbewerking.py): x naar cm^-1, y naar absorbantie, op het
raster van 4 cm^-1, normaliseren. Bestanden die niet te lezen zijn worden
overgeslagen en gelogd; het script crasht er niet op.
"""

from __future__ import annotations

import csv
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

PROJECTMAP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECTMAP))

from stofherkenner.jcamp_lezen import JcampFout, lees_jcamp_bestand  # noqa: E402
from stofherkenner.voorbewerking import RASTER, VoorbewerkingFout, bewerk_voor, x_naar_golfgetal  # noqa: E402

BRONMAP = PROJECTMAP / "data" / "raw" / "nist_ir"
DATAMAP = PROJECTMAP / "data"

# Wanneer noemen we twee spectra van DEZELFDE stof duplicaten?
# Regel 1: hun cosinusgelijkenis op het raster is minstens 0,99. Dat zijn in de
#          praktijk dezelfde metingen die alleen in resolutie (of nauwelijks)
#          verschillen. De drempel is gekozen op basis van de verdeling in de
#          data; zie docs/evaluatie.md.
# Regel 2: ze komen allebei uit de NIST-reeks "QUANT-IR". Die reeks bevat van
#          elke stof dezelfde gasmeting bij 5 resoluties en een paar
#          concentraties/temperaturen; dat zijn dus per definitie geen
#          onafhankelijke metingen.
DUPLICAAT_DREMPEL = 0.99
RESOLUTIEREEKS = "QUANT-IR"


def bepaal_fase(toestand: str) -> str:
    """Vat de vrije tekst uit ##STATE samen tot een van vijf categorieen."""
    t = toestand.lower()
    if not t.strip():
        return "onbekend"
    if t.startswith(("gas", "vapor", "vapour")):
        return "gas"
    if "solution" in t or "soln" in t:
        return "oplossing"
    if any(w in t for w in ("solid", "kbr", "mull", "nujol", "pellet", "crystal", "powder")):
        return "vast"
    if any(w in t for w in ("liquid", "neat", "film", "melt")):
        return "vloeistof"
    return "onbekend"


def korte_reden(fout: Exception) -> str:
    """Maak van een foutmelding een korte categorie, zodat we kunnen tellen."""
    tekst = str(fout)
    if "geen datablok" in tekst:
        return "geen meetpunten in het bestand (alleen gescande afbeelding)"
    if "y-eenheid" in tekst:
        return "y-eenheid niet bruikbaar (reflectie / brekingsindex e.d.)"
    if "x-eenheid" in tekst:
        return "x-eenheid onbekend"
    if "bedekt maar" in tekst:
        return "bedekt minder dan de helft van 550-3800 cm^-1"
    if "vlak" in tekst:
        return "spectrum is volledig vlak"
    return tekst[:80]


def masker_cosinus(a: np.ndarray, ma: np.ndarray, b: np.ndarray, mb: np.ndarray) -> float:
    """Cosinusgelijkenis van twee spectra, alleen over het deel dat ze allebei gemeten hebben."""
    beide = ma & mb
    if beide.sum() < 50:
        return 0.0
    noemer = np.linalg.norm(a[beide]) * np.linalg.norm(b[beide])
    return float(a[beide] @ b[beide] / noemer) if noemer > 0 else 0.0


def markeer_duplicaten(nist_ids: list[str], bronnen: list[str], spectra: np.ndarray, maskers: np.ndarray) -> np.ndarray:
    """Markeer bijna-identieke spectra van dezelfde stof.

    Geeft per spectrum de index van het "origineel" terug waarvan het een
    duplicaat is, of -1 als het spectrum uniek is. Het eerste spectrum van een
    groepje blijft altijd het origineel.
    """
    duplicaat_van = np.full(len(nist_ids), -1, dtype=np.int64)
    per_stof: dict[str, list[int]] = {}
    for i, nist_id in enumerate(nist_ids):
        per_stof.setdefault(nist_id, []).append(i)
    for indexen in per_stof.values():
        unieke: list[int] = []
        for i in indexen:
            for j in unieke:
                zelfde_reeks = bronnen[i] == RESOLUTIEREEKS and bronnen[j] == RESOLUTIEREEKS
                if zelfde_reeks or masker_cosinus(spectra[i], maskers[i], spectra[j], maskers[j]) >= DUPLICAAT_DREMPEL:
                    duplicaat_van[i] = j
                    break
            else:
                unieke.append(i)
    return duplicaat_van


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows-console: speciale tekens niet laten crashen
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    bestanden = sorted(BRONMAP.glob("*.jdx"))
    if not bestanden:
        print(f"FOUT: geen .jdx-bestanden gevonden in {BRONMAP}.\nDraai eerst: python scripts/download_database.py", file=sys.stderr)
        return 1

    start = time.time()
    spectra: list[np.ndarray] = []
    maskers: list[np.ndarray] = []
    rijen: list[dict] = []
    overgeslagen: list[tuple[str, str, str]] = []

    for teller, pad in enumerate(bestanden, 1):
        if teller % 2000 == 0:
            print(f"  {teller} / {len(bestanden)} bestanden verwerkt...", flush=True)
        try:
            spectrum = lees_jcamp_bestand(pad)
            voorbewerkt = bewerk_voor(spectrum)
        except (JcampFout, VoorbewerkingFout) as fout:
            overgeslagen.append((pad.name, korte_reden(fout), str(fout)))
            continue
        except Exception as fout:  # onverwacht: loggen en doorgaan, nooit crashen
            overgeslagen.append((pad.name, f"onverwachte fout ({type(fout).__name__})", str(fout)))
            continue

        # Bestandsnaam = {NIST Compound ID}_IR_{index}.jdx
        nist_id, _, index = pad.stem.partition("_IR_")
        golfgetal = np.sort(x_naar_golfgetal(spectrum.x, voorbewerkt.x_soort))
        stappen = np.diff(golfgetal)
        spectra.append(voorbewerkt.absorbantie.astype(np.float32))
        maskers.append(voorbewerkt.masker)
        rijen.append({
            "bestand": pad.name,
            "nist_id": nist_id,
            "spectrum_index": index,
            "naam": spectrum.titel,
            "cas": spectrum.cas,
            "formule": spectrum.formule,
            "fase": bepaal_fase(spectrum.toestand),
            "toestand": spectrum.toestand,
            "bron": spectrum.labels.get("$NIST SOURCE", ""),
            "x_soort": voorbewerkt.x_soort,
            "y_soort": voorbewerkt.y_soort,
            "aantal_punten": spectrum.x.size,
            "stap_cm": round(float(np.median(stappen)), 3) if stappen.size else 0.0,
            "dekking": round(voorbewerkt.dekking, 3),
            "npoints_klopt": spectrum.npoints_label == spectrum.x.size,
        })

    matrix = np.vstack(spectra)
    masker_matrix = np.vstack(maskers)

    print("Duplicaten markeren...", flush=True)
    duplicaat_van = markeer_duplicaten([r["nist_id"] for r in rijen], [r["bron"] for r in rijen], matrix, masker_matrix)
    for i, rij in enumerate(rijen):
        rij["duplicaat_van"] = int(duplicaat_van[i])

    # --- Opslaan ---
    np.savez_compressed(DATAMAP / "library.npz", spectra=matrix, maskers=masker_matrix, raster=RASTER)
    with open(DATAMAP / "metadata.csv", "w", newline="", encoding="utf-8") as f:
        schrijver = csv.DictWriter(f, fieldnames=list(rijen[0].keys()))
        schrijver.writeheader()
        schrijver.writerows(rijen)
    with open(DATAMAP / "overgeslagen.csv", "w", newline="", encoding="utf-8") as f:
        schrijver = csv.writer(f)
        schrijver.writerow(["bestand", "reden", "detail"])
        schrijver.writerows(overgeslagen)

    # --- Samenvatting ---
    redenen = Counter(reden for _, reden, _ in overgeslagen)
    uniek = int((duplicaat_van < 0).sum())
    regels = [
        f"Bestanden gevonden          : {len(bestanden)}",
        f"Spectra in de bibliotheek   : {len(rijen)}",
        f"  waarvan uniek             : {uniek}",
        f"  waarvan duplicaat         : {len(rijen) - uniek}  (zelfde stof en cosinus >= {DUPLICAAT_DREMPEL}, of zelfde {RESOLUTIEREEKS}-resolutiereeks)",
        f"Verschillende stoffen       : {len({r['nist_id'] for r in rijen})}",
        f"Overgeslagen bestanden      : {len(overgeslagen)}",
    ]
    regels += [f"  - {aantal:5d} x {reden}" for reden, aantal in redenen.most_common()]
    regels.append("Fase (alle spectra in de bibliotheek):")
    regels += [f"  - {aantal:5d} x {fase}" for fase, aantal in Counter(r["fase"] for r in rijen).most_common()]
    regels.append("Oorspronkelijke x-eenheid:")
    regels += [f"  - {aantal:5d} x {s}" for s, aantal in Counter(r["x_soort"] for r in rijen).most_common()]
    regels.append("Oorspronkelijke y-eenheid:")
    regels += [f"  - {aantal:5d} x {s}" for s, aantal in Counter(r["y_soort"] for r in rijen).most_common()]
    regels.append(f"##NPOINTS klopt niet met het echte aantal punten: {sum(not r['npoints_klopt'] for r in rijen)} spectra")
    regels.append(f"Rekentijd: {time.time() - start:.0f} s")
    samenvatting = "\n".join(regels)
    (DATAMAP / "build_log.txt").write_text(samenvatting + "\n", encoding="utf-8")
    print("\n" + samenvatting)
    return 0


if __name__ == "__main__":
    sys.exit(main())
