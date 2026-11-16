"""Voert de codecellen van een notebook uit in één Python-proces en slaat de echte uitvoer op.

Nodig omdat in de omgeving van de AI-assistent een Jupyter-kernel geen verbinding
via localhost kan maken. Elke cel draait echt (exec in een gedeelde namespace);
tekstuitvoer en matplotlib-figuren worden als notebook-uitvoer bewaard.
"""
import base64
import contextlib
import io
import os
import sys
import traceback
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import nbformat  # noqa: E402

pad = Path(sys.argv[1]).resolve()
os.chdir(pad.parent)                      # zoals Jupyter: werkmap = map van het notebook
nb = nbformat.read(pad, as_version=4)
namespace = {"__name__": "__main__"}
huidige_uitvoer = []


def toon_figuur(*args, **kwargs):
    for nummer in plt.get_fignums():
        fig = plt.figure(nummer)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
        huidige_uitvoer.append(nbformat.v4.new_output(
            "display_data", data={"image/png": base64.b64encode(buf.getvalue()).decode(), "text/plain": "<Figure>"}))
    plt.close("all")


plt.show = toon_figuur
teller = 0
fouten = 0
for cel in nb.cells:
    if cel.cell_type != "code":
        continue
    teller += 1
    huidige_uitvoer = []
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(compile(cel.source, f"<cel {teller}>", "exec"), namespace)
        fout = None
    except Exception as e:
        fout = e
    tekst = stdout.getvalue()
    uitvoer = []
    if tekst:
        uitvoer.append(nbformat.v4.new_output("stream", name="stdout", text=tekst))
    uitvoer.extend(huidige_uitvoer)
    if fout is not None:
        fouten += 1
        uitvoer.append(nbformat.v4.new_output("error", ename=type(fout).__name__, evalue=str(fout),
                                              traceback=traceback.format_exception(fout)))
    cel.outputs = uitvoer
    cel.execution_count = teller
    if plt.get_fignums():
        toon_figuur()
        cel.outputs.extend(huidige_uitvoer)

nbformat.write(nb, pad)
print(f"{teller} codecellen uitgevoerd, {fouten} met een fout")
