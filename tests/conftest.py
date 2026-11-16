"""Gedeelde hulpmiddelen voor de tests (pytest laadt dit bestand automatisch)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECTMAP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECTMAP))

VOORBEELDMAP = PROJECTMAP / "research" / "voorbeeldspectra"
DATAMAP = PROJECTMAP / "data"


def maak_jcamp(
    x: np.ndarray,
    y: np.ndarray,
    titel: str = "Testspectrum",
    x_eenheid: str = "1/CM",
    y_eenheid: str = "ABSORBANCE",
    per_regel: int = 10,
    npoints: int | None = None,
    extra_labels: str = "",
) -> str:
    """Maak de tekst van een geldig JCAMP-DX-bestand met een XYDATA-blok.

    ``x`` moet een vaste stapgrootte hebben. Met ``npoints`` kun je expres een
    verkeerd aantal in de kop zetten.
    """
    regels = [
        f"##TITLE={titel}",
        "##JCAMP-DX=4.24",
        "##DATA TYPE=INFRARED SPECTRUM",
        f"##XUNITS={x_eenheid}",
        f"##YUNITS={y_eenheid}",
        "##XFACTOR=1.0",
        "##YFACTOR=1.0",
        f"##FIRSTX={x[0]:.6f}",
        f"##LASTX={x[-1]:.6f}",
        f"##NPOINTS={len(x) if npoints is None else npoints}",
    ]
    if extra_labels:
        regels.append(extra_labels)
    regels.append("##XYDATA=(X++(Y..Y))")
    for begin in range(0, len(x), per_regel):
        waarden = " ".join(f"{v:.5f}" for v in y[begin:begin + per_regel])
        regels.append(f"{x[begin]:.4f} {waarden}")
    regels.append("##END=")
    return "\n".join(regels) + "\n"


def gauss(x: np.ndarray, midden: float, hoogte: float, breedte: float) -> np.ndarray:
    """Een klokvormige piek (Gauss-curve) met gegeven midden, hoogte en breedte (sigma)."""
    return hoogte * np.exp(-0.5 * ((x - midden) / breedte) ** 2)


@pytest.fixture(scope="session")
def voorbeeldmap() -> Path:
    return VOORBEELDMAP


@pytest.fixture(scope="session")
def bibliotheek():
    """De echte referentiebibliotheek; tests die hem nodig hebben worden overgeslagen als hij ontbreekt."""
    if not (DATAMAP / "library.npz").exists():
        pytest.skip("referentiebibliotheek ontbreekt (draai eerst setup.bat)")
    from stofherkenner.matching import laad_bibliotheek
    return laad_bibliotheek(DATAMAP)


@pytest.fixture()
def geldig_bestand() -> bytes:
    """Een klein, geldig JCAMP-DX-bestand met twee pieken."""
    x = np.arange(500.0, 4000.0 + 0.1, 2.0)
    y = gauss(x, 1715, 1.0, 12) + gauss(x, 2950, 0.5, 20) + 0.01
    return maak_jcamp(x, y).encode("utf-8")
