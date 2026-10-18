#!/usr/bin/env python3
"""Genera la lista de precios bajos (<100) pendientes de revision manual.

No sobrescribe una lista ya rellenada: si el archivo existe, pide renombrarlo.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "outputs" / "validacion" / "revision_precios_bajos.csv"
UMBRAL = 100

VEREDICTOS = "venta | alquiler | producto | error | no_verificable"


def newest_master() -> Path:
    files = sorted(MASTER_DIR.glob("dataset_maestro_*.csv"))
    if not files:
        raise FileNotFoundError("No hay dataset maestro en outputs/integracion/")
    return files[-1]


def main():
    if OUT.exists():
        raise SystemExit(
            f"Ya existe {OUT} (posiblemente con respuestas). "
            "Renombralo antes de regenerar la lista para no perder la revision."
        )
    master = pd.read_csv(newest_master(), dtype=str)
    precio = pd.to_numeric(master["precio_original"], errors="coerce")
    sospechoso = master["precio_sospechoso"].astype(str).str.lower().isin(["true", "1"])
    bajos = master[precio.notna() & (precio > 0) & (precio < UMBRAL) & ~sospechoso].copy()
    bajos["precio_original"] = precio[bajos.index]
    bajos = bajos.sort_values(["fuente", "precio_original"])

    tabla = bajos[["fuente", "id_local", "precio_original", "moneda", "titulo", "url"]].copy()
    tabla["veredicto"] = ""
    tabla["observacion"] = ""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Lista: {OUT}")
    print(f"Precios pendientes: {len(tabla)}")
    print(f"Rellenar veredicto con: {VEREDICTOS}")


if __name__ == "__main__":
    main()
