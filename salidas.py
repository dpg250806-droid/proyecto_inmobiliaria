"""Helpers for creating dated outputs without replacing earlier artifacts."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def nueva_ruta_salida(
    directory: Path,
    filename: str,
    stamp: str | None = None,
) -> Path:
    """Return a dated path not already present in ``directory``."""
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    name = Path(filename)
    candidate = directory / f"{name.stem}_{stamp}{name.suffix}"
    version = 2
    while candidate.exists():
        candidate = directory / f"{name.stem}_{stamp}_{version:02d}{name.suffix}"
        version += 1
    return candidate
