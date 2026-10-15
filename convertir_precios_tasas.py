#!/usr/bin/env python3
"""Normaliza precios a USD usando tasas informal y formal registradas."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
RATE_DIR = ROOT / "data" / "tasas"
OUT = ROOT / "outputs" / "conversiones"


def latest_file(directory: Path, pattern: str) -> Path:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No encontro {pattern} en {directory}")
    return files[-1]


def to_float(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalizar_moneda(value):
    if pd.isna(value):
        return None
    return str(value).strip().upper()


def convertir(frame: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    r = rates.iloc[0]
    fx_usd_inf = to_float(r.get("usd_informal_cup"))
    fx_eur_inf = to_float(r.get("eur_informal_cup"))
    fx_usd_for = to_float(r.get("usd_formal_cup"))
    fx_eur_for = to_float(r.get("eur_formal_cup"))
    fecha = str(r.get("fecha_utc", "sin_fecha"))

    def usd_price(row, fx_usd, fx_eur):
        price = to_float(row.get("precio_original", None))
        moneda = normalizar_moneda(row.get("moneda", None))
        if price is None:
            return None
        if moneda == "USD":
            return price
        if moneda == "EUR":
            if fx_usd is None or fx_eur is None:
                return None
            return price * fx_eur / fx_usd
        if moneda == "CUP":
            return price / fx_usd if fx_usd else None
        return None

    frame = frame.copy()
    frame["precio_usd_informal"] = frame.apply(lambda row: usd_price(row, fx_usd_inf, fx_eur_inf), axis=1)
    frame["precio_usd_formal"] = frame.apply(lambda row: usd_price(row, fx_usd_for, fx_eur_for), axis=1)
    frame["fx_usd_informal_cup"] = fx_usd_inf
    frame["fx_eur_informal_cup"] = fx_eur_inf
    frame["fx_usd_formal_cup"] = fx_usd_for
    frame["fx_eur_formal_cup"] = fx_eur_for
    frame["fecha_tasa"] = fecha
    frame["divergencia_informal_formal_usd_pct"] = 100 * (frame["precio_usd_informal"] / frame["precio_usd_formal"] - 1)
    return frame


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master_path = latest_file(MASTER_DIR, "dataset_maestro_*.csv")
    rate_path = latest_file(RATE_DIR, "tasas_cambio_*.csv")
    frame = pd.read_csv(master_path, dtype=str)
    rates = pd.read_csv(rate_path, dtype=str)
    converted = convertir(frame, rates)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = OUT / f"dataset_maestro_conversion_{stamp}.csv"
    converted.to_csv(output, index=False, encoding="utf-8-sig")

    stats = converted.groupby(["fuente", "moneda"]).agg(
        anuncios=("precio_original", "count"),
        convertidos_usd_informal=("precio_usd_informal", lambda s: pd.notna(s).sum()),
        mediana_usd_informal=("precio_usd_informal", "median"),
        mediana_usd_formal=("precio_usd_formal", "median"),
    ).reset_index()
    stats_path = OUT / f"resumen_conversion_{stamp}.csv"
    stats.to_csv(stats_path, index=False, encoding="utf-8-sig")

    print(f"Dataset con conversion: {output}")
    print(f"Mediana informal/formal guardada en: {stats_path}")
    print(stats.to_string(index=False))


if __name__ == "__main__":
    main()