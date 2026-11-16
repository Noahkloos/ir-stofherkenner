"""Plotly-grafieken voor de app.

Twee grafieken:
- ``spectrum_grafiek``: het geuploade spectrum met de gevonden pieken gemarkeerd;
- ``overlay_grafiek`` : het geuploade spectrum en een referentiespectrum over elkaar.

Bij IR is het gebruikelijk om het golfgetal van HOOG naar LAAG te tekenen
(4000 links, 500 rechts); daarom staat de x-as omgekeerd.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .piekdetectie import Piek

KLEUR_MONSTER = "#1f4e79"      # donkerblauw: het geuploade spectrum
KLEUR_REFERENTIE = "#d9480f"   # oranje: het referentiespectrum
KLEUR_PIEK = "#c92a2a"         # rood: gemarkeerde pieken
MAX_PUNTEN_IN_GRAFIEK = 4000   # meer punten ziet niemand, en het maakt de browser traag
MAX_PIEKLABELS = 14            # alleen de belangrijkste pieken krijgen een getal erbij

# Instellingen die de grafiek laten meeschalen met het scherm (desktop en tablet)
PLOTLY_CONFIG = {"responsive": True, "displaylogo": False, "scrollZoom": False}


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
    """Opmaak die beide grafieken delen."""
    fig.update_layout(
        height=hoogte,
        autosize=True,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        template="plotly_white",
    )
    fig.update_xaxes(title_text="Golfgetal (cm⁻¹)", autorange="reversed", showgrid=True, automargin=True)
    fig.update_yaxes(title_text=y_titel, showgrid=True, automargin=True)
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
    """
    volgorde = np.argsort(golfgetal)
    x_gesorteerd, y_gesorteerd = golfgetal[volgorde], y[volgorde]
    x_dun, y_dun = dun_uit(x_gesorteerd, y_gesorteerd)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_dun, y=y_dun, name=naam,
        mode="markers" if losse_punten else "lines",
        line=dict(color=KLEUR_MONSTER, width=1.6),
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
            x=piek_x, y=piek_y, name="Gedetecteerde pieken",
            mode="markers+text", text=labels,
            textposition="bottom center" if pieken_omlaag else "top center",
            textfont=dict(size=11, color=KLEUR_PIEK),
            marker=dict(color=KLEUR_PIEK, size=7, symbol="circle"),
            hovertemplate="piek bij %{x:.0f} cm⁻¹<extra></extra>",
            cliponaxis=False,
        ))
    return _basis_opmaak(fig, y_titel, hoogte=430)


def overlay_grafiek(
    raster: np.ndarray,
    monster: np.ndarray,
    monster_masker: np.ndarray,
    referentie: np.ndarray,
    referentie_masker: np.ndarray,
    referentie_naam: str,
) -> go.Figure:
    """Teken het geuploade spectrum en een referentiespectrum over elkaar (beide genormaliseerd)."""
    # Buiten het gemeten bereik tekenen we niets (NaN = gat in de lijn)
    monster_lijn = np.where(monster_masker, monster, np.nan)
    referentie_lijn = np.where(referentie_masker, referentie, np.nan)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=raster, y=referentie_lijn, name=f"Referentie: {referentie_naam}", mode="lines",
        line=dict(color=KLEUR_REFERENTIE, width=1.6),
        fill="tozeroy", fillcolor="rgba(217,72,15,0.12)",
        hovertemplate="referentie: %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=raster, y=monster_lijn, name="Geüpload spectrum", mode="lines",
        line=dict(color=KLEUR_MONSTER, width=1.6),
        hovertemplate="geüpload: %{y:.2f}<extra></extra>",
    ))
    return _basis_opmaak(fig, "Genormaliseerde absorbantie", hoogte=400)
