#!/usr/bin/env python3
"""Aplica correcciones manuales verificadas a HogarEnCuba."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parent
HOGAR_DIR = ROOT / "outputs" / "hogarencuba"
MANUAL = HOGAR_DIR / "revision_manual_hogarencuba.csv"


def latest_hogar() -> Path:
    candidates = []
    for p in HOGAR_DIR.glob("viviendas_hogarencuba_*.csv"):
        try:
            if p.stat().st_size > 0 and len(pd.read_csv(p, dtype=str)) > 0:
                candidates.append(p)
        except Exception:
            continue
    if not candidates:
        raise FileNotFoundError("No hay CSV valido de HogarEnCuba")
    return max(candidates, key=lambda p: (len(pd.read_csv(p, dtype=str)), p.name))


def main():
    base_path = latest_hogar()
    frame = pd.read_csv(base_path, dtype=str)
    manual = pd.read_csv(MANUAL, dtype=str)

    for _, row in manual.iterrows():
        idx = frame.index[frame["id_local"].astype(str) == str(row["id_local"])]
        if len(idx) == 0:
            continue
        i = idx[0]
        field = str(row["campo"]).strip()
        value = row["valor"]
        if field in frame.columns:
            frame.at[i, field] = value
        if field == "precio_original":
            frame.at[i, "precio_sospechoso"] = "False"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = HOGAR_DIR / f"viviendas_hogarencuba_revisada_{stamp}.csv"
    frame.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Base: {base_path.name}")
    print(f"Salida: {out}")
    print(f"Correcciones aplicadas: {len(manual)}")
    for _, row in manual.iterrows():
        print(f"  {row['id_local']}: {row['campo']} = {row['valor']}")


if __name__ == "__main__":
    main()