"""Eerlijke test op de tien voorbeeldbestanden (bron voor docs/demo_script.md).

Gebruik:  .venv\Scripts\python scripts\demo_eerlijke_test.py

Elk voorbeeldbestand staat zelf in de bibliotheek en scoort daardoor 100%.
Hier doet het identieke referentiespectrum NIET mee (negeer_identiek=True),
zodat je ziet of de app de stof ook via een ANDERE meting herkent.
Uitvoer: docs/demo_eerlijke_test.txt
"""
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from stofherkenner.analyse import analyseer, lees_en_valideer  # noqa: E402
from stofherkenner.matching import laad_bibliotheek  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    bib = laad_bibliotheek(root / "data")
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        print("Eerlijke test: het identieke spectrum doet niet mee. Gemaakt door scripts/demo_eerlijke_test.py\n")
        for p in sorted((root / "research/voorbeeldspectra").glob("*.jdx")):
            a = analyseer(lees_en_valideer(p.name, p.read_bytes()), bib, negeer_identiek=True)
            juist = a.spectrum.cas
            plek = next((r.rang for r in a.top.itertuples() if r.cas == juist), "niet in top 5")
            print(f"=== {p.name} | juiste stof: {a.spectrum.titel} ({juist}) | plek juiste stof: {plek}")
            for r in a.top.itertuples():
                print(f"   #{r.rang} {r.score:5.1f}%  {r.naam[:45]:45s} {r.cas:12s} [{r.fase}] {r.formule}")
            for w in a.zoek_waarschuwingen:
                print("   WAARSCHUWING:", w)
            if not a.zoek_waarschuwingen:
                print("   (geen waarschuwing)")
            print()
    tekst = buffer.getvalue()
    (root / "docs" / "demo_eerlijke_test.txt").write_text(tekst, encoding="utf-8")
    print(tekst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
