"""Onderzoek (RS): worden de kandidaat-bibliotheken nog onderhouden?

Draaien:  .venv\\Scripts\\python research\\onderhoud_bibliotheken.py     (internet nodig)

Haalt per bibliotheek live op:
- van PyPI: nieuwste versie, datum van die release, datum van de eerste release,
  aantal releases, vereiste Python-versie en de korte omschrijving;
- van GitHub: datum van de laatste commit en of de repository gearchiveerd is.

Zo staat er in de documentatie niets uit het hoofd, maar alleen wat op de
dag van het onderzoek echt is opgezocht.

Uitvoer: research/resultaten/onderhoud.md en onderhoud.csv
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

RESULTAATMAP = Path(__file__).resolve().parent / "resultaten"

# pakketnaam op PyPI -> GitHub-repository (eigenaar/naam)
BIBLIOTHEKEN = {
    "jcamp": "nzhagen/jcamp",
    "nmrglue": "jjhelmus/nmrglue",
    "spectrochempy": "spectrochempy/spectrochempy",
    "chemparse": "gmboyer/chemparse",
}


def haal_json(url: str):
    verzoek = urllib.request.Request(url, headers={"User-Agent": "onderzoek-jcamp-bibliotheken"})
    with urllib.request.urlopen(verzoek, timeout=30) as antwoord:
        return json.load(antwoord)


def pypi_info(pakket: str) -> dict:
    d = haal_json(f"https://pypi.org/pypi/{pakket}/json")
    info = d["info"]
    datums = sorted(bestanden[0]["upload_time"][:10] for bestanden in d["releases"].values() if bestanden)
    nieuwste = d["releases"].get(info["version"]) or []
    urls = " ".join(str(u) for u in (info.get("project_urls") or {}).values()) + " " + str(info.get("home_page") or "")
    return {
        "nieuwste_versie": info["version"],
        "datum_nieuwste_release": nieuwste[0]["upload_time"][:10] if nieuwste else "?",
        "eerste_release": datums[0] if datums else "?",
        "aantal_releases": len(datums),
        "vereist_python": info.get("requires_python") or "niet opgegeven",
        "omschrijving": (info.get("summary") or "").strip(),
        "links": urls,
    }


def github_info(repo: str) -> dict:
    try:
        r = haal_json(f"https://api.github.com/repos/{repo}")
        commits = haal_json(f"https://api.github.com/repos/{r['full_name']}/commits?per_page=1")
        return {
            "repository": r["full_name"],
            "laatste_commit": commits[0]["commit"]["committer"]["date"][:10],
            "gearchiveerd": "ja" if r.get("archived") else "nee",
            "sterren": r.get("stargazers_count"),
            "open_issues": r.get("open_issues_count"),
        }
    except Exception as fout:
        return {"repository": f"{repo} (niet gevonden: {type(fout).__name__})", "laatste_commit": "?",
                "gearchiveerd": "?", "sterren": "?", "open_issues": "?"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    RESULTAATMAP.mkdir(parents=True, exist_ok=True)
    rijen = []
    for pakket, repo in BIBLIOTHEKEN.items():
        rij = {"bibliotheek": pakket, **pypi_info(pakket), **github_info(repo)}
        rijen.append(rij)
        print(f"{pakket:14s} v{rij['nieuwste_versie']:8s} release {rij['datum_nieuwste_release']}  laatste commit {rij['laatste_commit']}  "
              f"python {rij['vereist_python']:14s} {rij['repository']}  |  {rij['omschrijving'][:70]}")

    with open(RESULTAATMAP / "onderhoud.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[k for k in rijen[0] if k != "links"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rijen)

    tabel = "\n".join(
        f"| {r['bibliotheek']} | {r['omschrijving']} | {r['nieuwste_versie']} | {r['datum_nieuwste_release']} | {r['laatste_commit']} | "
        f"{r['eerste_release']} | {r['aantal_releases']} | {r['vereist_python']} | {r['gearchiveerd']} | {r['repository']} |"
        for r in rijen)
    rapport = f"""# Onderhoud van de kandidaat-bibliotheken

> Automatisch opgezocht door `research/onderhoud_bibliotheken.py` op {date.today().isoformat()} (bronnen: de PyPI-API en de GitHub-API).

| Bibliotheek | Omschrijving volgens PyPI | Nieuwste versie | Datum nieuwste release | Laatste commit (GitHub) | Eerste release | Aantal releases | Vereiste Python | Gearchiveerd? | Repository |
|---|---|---|---|---|---|---|---|---|---|
{tabel}
"""
    (RESULTAATMAP / "onderhoud.md").write_text(rapport, encoding="utf-8")
    print(f"Rapport: {RESULTAATMAP / 'onderhoud.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
