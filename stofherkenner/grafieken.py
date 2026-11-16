"""Plotly-grafieken voor de app, in de stijl van klassieke IR-software.

Twee grafieken:
- ``spectrum_grafiek``: het geuploade spectrum met de gevonden pieken als rode
  stippen. Op een stip kun je klikken (de app toont dan welke binding het kan zijn).
- ``overlay_grafiek`` : het geuploade spectrum met een of meer referentiespectra
  uit de top 5 eroverheen.

Stijl: witte meetgrafiek met een zwart kader en maatstreepjes aan de buitenkant,
lichtgrijze stippellijnen als raster, zoals in veel spectrometersoftware.
Bij IR is het gebruikelijk om het golfgetal van HOOG naar LAAG te tekenen
(4000 links, 500 rechts); daarom staat de x-as omgekeerd.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go

from .piekdetectie import Piek

KLEUR_MONSTER = "#0a246a"      # donker marineblauw: het geuploade spectrum
KLEUR_PIEK = "#d40000"         # rood: gemarkeerde pieken
KLEUR_PIEK_GEKOZEN = "#ffcc00" # geel met rode rand: aangeklikte piek
# Vijf goed te onderscheiden kleuren voor de top-5-referenties
KLEUREN_REFERENTIES = ("#e8590c", "#2b8a3e", "#7048e8", "#c2255c", "#0b7285")
LETTERTYPE = "Segoe UI, Tahoma, Geneva, Verdana, sans-serif"
MAX_PUNTEN_IN_GRAFIEK = 4000   # meer punten ziet niemand, en het maakt de browser traag
MAX_PIEKLABELS = 14            # alleen de belangrijkste pieken krijgen een getal erbij
NAAM_PIEKEN = "Gedetecteerde pieken"

# Instellingen die de grafiek laten meeschalen met het scherm (desktop en tablet)
PLOTLY_CONFIG = {"responsive": True, "displaylogo": False, "scrollZoom": False,
                 "modeBarButtonsToRemove": ["select2d", "lasso2d"]}


@dataclass
class Referentie:
    """Een referentiespectrum om over het geuploade spectrum heen te leggen."""

    naam: str
    absorbantie: np.ndarray
    masker: np.ndarray


def dun_uit(x: np.ndarray, y: np.ndarray, max_punten: int = MAX_PUNTEN_IN_GRAFIEK) -> tuple[np.ndarray, np.ndarray]:
    """Verminder het aantal punten voor de grafiek zonder pieken kwijt te raken.

    Een spectrum van 5 MB heeft honderdduizenden punten; dat tekenen is traag.
    We verdelen het spectrum in blokjes en bewaren van elk blokje het laagste
    en het hoogste punt. Zo blijft elke piek (en elk dal) zichtbaar.
    """
    n = x.size
    if n <= max_punten:
        return x, y
    blok = int(np.ceil(n / (max_punten // 2)))
    aantal_blokken = n // blok
    xb = x[:aantal_blokken * blok].reshape(aantal_blokken, blok)
    yb = y[:aantal_blokken * blok].reshape(aantal_blokken, blok)
    rij = np.arange(aantal_blokken)
    i_min, i_max = yb.argmin(axis=1), yb.argmax(axis=1)
    eerste, tweede = np.minimum(i_min, i_max), np.maximum(i_min, i_max)   # volgorde binnen het blokje behouden
    x_uit = np.column_stack((xb[rij, eerste], xb[rij, tweede])).ravel()
    y_uit = np.column_stack((yb[rij, eerste], yb[rij, tweede])).ravel()
    return x_uit, y_uit


def _basis_opmaak(fig: go.Figure, y_titel: str, hoogte: int) -> go.Figure:
    """Opmaak die beide grafieken delen: wit vlak, zwart kader, klassieke assen."""
    as_stijl = dict(
        showline=True, linecolor="black", linewidth=1, mirror=True,          # zwart kader rondom
        ticks="outside", tickcolor="black", ticklen=5,
        showgrid=True, gridcolor="#d9d9d9", griddash="dot",
        zeroline=False, automargin=True,
        title_font=dict(size=13), tickfont=dict(size=12),
    )
    fig.update_layout(
        height=hoogte,
        autosize=True,
        margin=dict(l=10, r=14, t=36, b=10),
        font=dict(family=LETTERTYPE, size=12, color="#000000"),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                    bgcolor="rgba(255,255,255,0.9)", bordercolor="#a0a0a0", borderwidth=1, font=dict(size=11)),
        hovermode="closest",
        hoverlabel=dict(bgcolor="#ffffe1", bordercolor="#767676", font=dict(family=LETTERTYPE, color="#000000")),
        clickmode="event+select",
    )
    fig.update_xaxes(title_text="Golfgetal (cm⁻¹)", autorange="reversed", **as_stijl)
    fig.update_yaxes(title_text=y_titel, **as_stijl)
    return fig


def spectrum_grafiek(
    golfgetal: np.ndarray,
    y: np.ndarray,
    y_titel: str,
    pieken: list[Piek],
    naam: str = "Geüpload spectrum",
    losse_punten: bool = False,
) -> go.Figure:
    """Teken het spectrum met de gevonden pieken als rode stippen.

    ``y`` mag transmissie of absorbantie zijn; de stippen worden op de lijn
    gezet (bij transmissie wijzen pieken dus naar beneden).
    De pieken zitten in een apart "spoor" met de naam ``NAAM_PIEKEN``;
    daaraan herkent de app een klik op een stip.

    Let op: de figuur mag NIET veranderen als je op een stip klikt. Streamlit
    herkent een grafiek aan zijn inhoud; een andere figuur = een "nieuwe"
    grafiek en dan is de klik weer vergeten. Het oplichten van de aangeklikte
    stip doet Plotly daarom zelf in de browser (``selected`` hieronder).
    """
    volgorde = np.argsort(golfgetal)
    x_gesorteerd, y_gesorteerd = golfgetal[volgorde], y[volgorde]
    x_dun, y_dun = dun_uit(x_gesorteerd, y_gesorteerd)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_dun, y=y_dun, name=naam,
        mode="markers" if losse_punten else "lines",
        line=dict(color=KLEUR_MONSTER, width=1.4),
        marker=dict(color=KLEUR_MONSTER, size=4),
        hovertemplate="%{x:.0f} cm⁻¹<br>%{y:.3g}<extra></extra>",
    ))

    if pieken:
        piek_x = np.array([p.golfgetal for p in pieken])
        piek_y = np.interp(piek_x, x_gesorteerd, y_gesorteerd)     # hoogte van de lijn op de piekpositie
        # Alleen de meest opvallende pieken krijgen een getal, anders wordt het onleesbaar
        belangrijkste = set(np.argsort([-p.prominentie for p in pieken])[:MAX_PIEKLABELS])
        labels = [f"{p.golfgetal:.0f}" if i in belangrijkste else "" for i, p in enumerate(pieken)]
        pieken_omlaag = np.nanmean(piek_y) < np.nanmedian(y_gesorteerd)   # transmissie: pieken wijzen omlaag
        fig.add_trace(go.Scatter(
            x=piek_x, y=piek_y, name=NAAM_PIEKEN,
            mode="markers+text", text=labels,
            textposition="bottom center" if pieken_omlaag else "top center",
            textfont=dict(size=11, color=KLEUR_PIEK),
            marker=dict(color=KLEUR_PIEK, size=10, symbol="circle", line=dict(color="#7a0000", width=1)),
            # Aangeklikte stip: groter en geel. Niet-aangeklikte stippen blijven gewoon zichtbaar
            # (Plotly maakt ze normaal doorzichtig; dat willen we niet).
            selected=dict(marker=dict(color=KLEUR_PIEK_GEKOZEN, size=16, opacity=1)),
            unselected=dict(marker=dict(opacity=1), textfont=dict(color=KLEUR_PIEK)),
            hovertemplate="piek bij %{x:.0f} cm⁻¹<br><i>klik voor de mogelijke binding</i><extra></extra>",
            cliponaxis=False,
        ))
    return _basis_opmaak(fig, y_titel, hoogte=440)


def pieken_uit_selectie(selectie, pieken: list[Piek], spoor_pieken: int = 1) -> list[float]:
    """Welke pieken heeft de gebruiker in de spectrumgrafiek aangeklikt?

    ``selectie`` is wat ``st.plotly_chart(on_select="rerun")`` teruggeeft (of een
    gewone dict met dezelfde opbouw). We kijken alleen naar punten uit het spoor
    met de rode stippen (``spoor_pieken``; spoor 0 is de lijn) en zoeken de piek
    op via zijn golfgetal, niet via een volgnummer. Zo kan een oude selectie
    nooit naar een verkeerde piek wijzen. Geeft de golfgetallen terug.
    """
    try:
        punten = (selectie["selection"]["points"] or []) if selectie else []
    except (AttributeError, KeyError, TypeError):
        return []
    bekend = {round(p.golfgetal): p.golfgetal for p in pieken}
    gekozen: list[float] = []
    for punt in punten:
        try:
            if punt.get("curve_number") != spoor_pieken or punt.get("x") is None:
                continue
            golfgetal = bekend.get(round(float(punt["x"])))
        except (AttributeError, TypeError, ValueError):
            continue
        if golfgetal is not None and golfgetal not in gekozen:
            gekozen.append(golfgetal)
    return gekozen


def overlay_grafiek(
    raster: np.ndarray,
    monster: np.ndarray,
    monster_masker: np.ndarray,
    referenties: list[Referentie],
) -> go.Figure:
    """Teken het geuploade spectrum met een of meer referentiespectra eroverheen (alles genormaliseerd).

    Bij één referentie wordt het vlak onder de referentie licht ingekleurd; bij
    meerdere niet, anders wordt het onoverzichtelijk.
    """
    fig = go.Figure()
    vullen = len(referenties) == 1
    for i, ref in enumerate(referenties):
        kleur = KLEUREN_REFERENTIES[i % len(KLEUREN_REFERENTIES)]
        fig.add_trace(go.Scatter(
            x=raster, y=np.where(ref.masker, ref.absorbantie, np.nan),   # NaN = gat buiten het meetbereik
            name=ref.naam, mode="lines",
            line=dict(color=kleur, width=1.3),
            fill="tozeroy" if vullen else None,
            fillcolor="rgba(232,89,12,0.10)" if vullen else None,
            hovertemplate=f"{ref.naam[:40]}: " + "%{y:.2f}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=raster, y=np.where(monster_masker, monster, np.nan), name="Geüpload spectrum", mode="lines",
        line=dict(color="#000000", width=1.8),
        hovertemplate="geüpload: %{y:.2f}<extra></extra>",
    ))
    fig = _basis_opmaak(fig, "Genormaliseerde absorbantie", hoogte=420)
    fig.update_layout(hovermode="x unified", clickmode="event")
    return fig
