#!/usr/bin/env python3
"""Limpieza integrada no destructiva de la base maestra."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

from precio_moneda import precios_analisis

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "outputs" / "limpieza_integrada"


def newest(directory: Path, pattern: str) -> Path:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(directory / pattern)
    return files[-1]


def normalizar_ubicacion(value):
    if pd.isna(value):
        return None
    text = str(value).strip().title().replace(" De La ", " de la ").replace(" Del ", " del ")
    return " ".join(text.split())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(newest(MASTER_DIR, "dataset_maestro_*.csv"), dtype=str)
    frame["ubicacion_normalizada"] = frame["ubicacion_raw"].map(normalizar_ubicacion)
    frame["precio_original"] = pd.to_numeric(frame["precio_original"], errors="coerce")
    frame["habitaciones"] = pd.to_numeric(frame["habitaciones"], errors="coerce")
    frame["banos"] = pd.to_numeric(frame["banos"], errors="coerce")
    frame["superficie_m2"] = pd.to_numeric(frame["superficie_m2"], errors="coerce") if "superficie_m2" in frame else pd.NA

    frame["precio_sospechoso"] = frame["precio_sospechoso"].astype(str).str.lower().isin(["true", "1"])
    frame.loc[(frame["fuente"] == "Revolico") & (frame["moneda"] == "CUP"), "precio_sospechoso"] = True
    # Recalcular el precio de analisis con la marca extra que aplica este script.
    frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    frame["canal_analisis"] = frame["fuente"].map({
        "Revolico": "clasificado_informal",
        "Cubisima": "plataforma_estructurada",
        "HogarEnCuba": "ficha_estructurada",
    }).fillna("desconocido")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"dataset_maestro_depurado_{stamp}.csv"
    frame.to_csv(path, index=False, encoding="utf-8-sig")

    summary = frame.groupby(["fuente", "canal_analisis"]).agg(
        anuncios=("precio_original", "size"),
        precio_valido=("precio_original", lambda s: pd.notna(s).sum()),
        precio_analisis=("precio_analisis", lambda s: pd.notna(s).sum()),
        sospechosos=("precio_sospechoso", lambda s: int(s.sum())),
        banos=("banos", lambda s: pd.notna(s).sum()),
        m2=("superficie_m2", lambda s: pd.notna(s).sum()),
    ).reset_index()
    summary.to_csv(OUT / f"resumen_limpieza_integrada_{stamp}.csv", index=False, encoding="utf-8-sig")

    print(f"Dataset depurado: {path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()