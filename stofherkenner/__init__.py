"""IR-Stofherkenner: herkent een stof aan de hand van een IR-spectrum.

Modules (elk met een eigen, kleine taak):
- jcamp_lezen.py        : JCAMP-DX-tekst omzetten naar getallen
- validatie.py          : strenge controle van een geupload bestand
- voorbewerking.py      : eenheden omrekenen, op vast raster zetten, normaliseren
- piekdetectie.py       : pieken zoeken en van ruis onderscheiden
- matching.py           : vergelijken met de referentiebibliotheek
- functionele_groepen.py: regels (expertsysteem) die pieken uitleggen
- grafieken.py          : Plotly-grafieken voor de app

Er wordt nergens een model getraind: alles is klassieke (symbolische) AI.
"""
