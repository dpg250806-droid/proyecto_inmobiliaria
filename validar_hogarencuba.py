#!/usr/bin/env python3
"""Validacion local de anuncios de HogarEnCuba."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parent
HOGAR_DIR = ROOT / "outputs" / "hogarencuba"
OUT = ROOT / "outputs" / "validacion"
REVISION_MANUAL = HOGAR_DIR / "revision_manual_hogarencuba.csv"


def latest_csv(directory: Path, pattern: str) -> Path:
    candidates = sorted(directory.glob(pattern))
    if not candidates:
        raise FileNotFoundError(directory / pattern)
    return candidates[-1]


def revision_manual() -> dict[str, list[str]]:
    """id_local -> campos verificados manualmente por el usuario."""
    if not REVISION_MANUAL.exists():
        return {}
    data = pd.read_csv(REVISION_MANUAL, dtype=str)
    verified: dict[str, list[str]] = {}
    for _, row in data.iterrows():
        verified.setdefault(str(row["id_local"]), []).append(str(row["campo"]))
    return verified


def validar(row, verified: dict[str, list[str]]) -> str:
    obs = []
    campos = verified.get(str(row.get("id_local")), [])
    if pd.isna(row.get("id_local")) or str(row.get("id_local")).strip() == "":
        obs.append("sin id")
    url = str(row.get("url", ""))
    if not url.startswith("https://hogarencuba.com/"):
        obs.append("url no verificable")
    price = pd.to_numeric(row.get("precio_original"), errors="coerce")
    if pd.isna(price) or price <= 0:
        obs.append("precio invalido")
    elif price > 1_000_000 and "precio_original" not in campos:
        obs.append("precio atipico")
    rooms = pd.to_numeric(row.get("habitaciones"), errors="coerce")
    if pd.isna(rooms) or rooms <= 0 or rooms > 20:
        obs.append("habitaciones no validas")
    baths = pd.to_numeric(row.get("banos"), errors="coerce")
    if pd.notna(baths) and (baths < 0 or baths > 20):
        obs.append("banos atipicos")
    area = pd.to_numeric(row.get("superficie_m2"), errors="coerce")
    if pd.notna(area) and (area < 10 or area > 10000) and "superficie_m2" not in campos:
        obs.append("m2 atipico")
    if pd.isna(row.get("ubicacion_raw")) or str(row.get("ubicacion_raw")).strip() == "":
        obs.append("sin municipio")
    if pd.isna(row.get("moneda")) or str(row.get("moneda")).strip() == "":
        obs.append("sin moneda")
    if not obs:
        return "valido (manual)" if campos else "valido"
    return "revisar: " + ", ".join(obs)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    verified = revision_manual()
    path = latest_csv(HOGAR_DIR, "viviendas_hogarencuba_*.csv")
    frame = pd.read_csv(path, dtype=str)
    frame["estado_validacion"] = frame.apply(lambda r: validar(r, verified), axis=1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT / f"validacion_hogarencuba_{stamp}.csv"
    frame.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Archivo validado: {path.name}")
    print(f"Salida: {out}")
    print(frame["estado_validacion"].value_counts().to_string())
    pendientes = frame[frame["estado_validacion"].str.startswith("revisar")]
    if len(pendientes) > 0:
        print("Pendientes:")
        print(pendientes[["id_local", "estado_validacion"]].to_string(index=False))


if __name__ == "__main__":
    main()
