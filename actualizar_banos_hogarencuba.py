#!/usr/bin/env python3
"""Aplica revision manual de banos a una copia de HogarEnCuba."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re

import pandas as pd

ROOT = Path(__file__).resolve().parent
HOGAR_DIR = ROOT / "outputs" / "hogarencuba"
REVISION = HOGAR_DIR / "revision_banos_hogarencuba.csv"


def latest_hogar() -> Path:
    candidates = sorted(HOGAR_DIR.glob("viviendas_hogarencuba_*.csv"))
    valid = []
    for p in candidates:
        try:
            if p.stat().st_size > 0 and len(pd.read_csv(p, dtype=str)) > 0:
                valid.append(p)
        except Exception:
            continue
    if not valid:
        raise FileNotFoundError("No hay CSV valido de HogarEnCuba")
    # Preferir el archivo con mas filas; en empate, el mas reciente.
    return max(valid, key=lambda p: (len(pd.read_csv(p, dtype=str)), p.name))


def verified_value(text):
    if pd.isna(text):
        return None
    text = str(text).strip()
    if not text:
        return None
    token = text.split(";")[0].strip()
    if token == "":
        return None
    try:
        return float(token)
    except ValueError:
        return None


def main():
    hogar_path = latest_hogar()
    frame = pd.read_csv(hogar_path, dtype=str)
    revision = pd.read_csv(REVISION, dtype=str)
    revision["banos_verificado"] = revision["observacion"].map(verified_value)

    lookup = dict(zip(revision["id_local"].astype(str), revision["banos_verificado"]))
    updated = 0
    for idx, row in frame.iterrows():
        if pd.isna(row.get("banos")) or str(row.get("banos")).strip() == "":
            value = lookup.get(str(row.get("id_local")))
            if value is not None:
                frame.at[idx, "banos"] = value
                updated += 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = HOGAR_DIR / f"viviendas_hogarencuba_revisada_{stamp}.csv"
    frame.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Archivo base: {hogar_path.name}")
    print(f"Archivo revisado: {out}")
    print(f"Filas: {len(frame)}")
    print(f"Banos actualizados: {updated}")
    print(f"Cobertura banos: {pd.to_numeric(frame['banos'], errors='coerce').notna().sum()}/{len(frame)}")


if __name__ == "__main__":
    main()