#!/usr/bin/env python3
"""Integra fuentes inmobiliarias cubanas en un dataset maestro no destructivo.

Uso:
    python integrar_fuentes.py
    python integrar_fuentes.py --sin-dedup
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent
STANDARD_COLUMNS = [
    "fuente",
    "snapshot_origen",
    "id_local",
    "titulo",
    "url",
    "tipo_vivienda",
    "ubicacion_raw",
    "zona_normalizada",
    "habitaciones",
    "banos",
    "superficie_m2",
    "precio_original",
    "moneda",
    "precio_sospechoso",
    "fecha_publicacion",
    "fecha_descarga",
    "garaje",
    "piscina",
    "terraza",
    "patio",
    "balcon",
    "jardin",
    "canal",
    "agencia_observada",
    "calidad_metadatos",
    "texto_evidencia",
    "observacion",
]


def normalizar_texto(value):
    if pd.isna(value):
        return value
    return str(value).strip().replace("  ", " ")


def normalizar_zona(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i")
    text = text.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    text = re.sub(r"\s+", " ", text)
    return text


def normalizar_precio(value, moneda) -> tuple[float | None, bool]:
    """Devuelve (precio_numerico, sospechoso) sin borrar valores atipicos."""
    if pd.isna(value):
        return None, True

    try:
        number = float(value)
    except (TypeError, ValueError):
        parsed = re.search(r"(\d[\d.,]*)", str(value))
        number = float(parsed.group(1).replace(".", "").replace(",", ".")) if parsed else None

    if number is None:
        return None, True
    if not np.isfinite(number):
        return None, True
    if number <= 0:
        return number, True
    if number == 1:
        return number, True
    if number > 1_000_000:
        return number, True
    if pd.isna(moneda) or str(moneda).strip().lower() in {"", "nan", "none"}:
        return number, True
    return number, False


def quality_score(row, required_fields):
    return sum(pd.notna(row.get(field)) and str(row.get(field)).strip() != "" for field in required_fields)


def dataframe_revolico(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    rows = []
    required = ["tipo_vivienda", "ubicacion_raw", "habitaciones", "precio_original", "moneda"]
    for idx, item in source.iterrows():
        price, suspicious = normalizar_precio(item.get("precio", ""), item.get("moneda", ""))
        if (not suspicious) and str(item.get("moneda", "")).strip().upper() == "CUP":
            suspicious = True
        rows.append(
            {
                "fuente": "Revolico",
                "snapshot_origen": str(path.name),
                "id_local": f"rev_{idx + 1:06d}_{pd.notna(item.get('url')) and item['url'][:60] or idx}",
                "titulo": normalizar_texto(item.get("titulo", "")),
                "url": normalizar_texto(item.get("url", "")),
                "tipo_vivienda": (str(item.get("titulo", "")).strip().split()[0].lower() if pd.notna(item.get("titulo", "")) and str(item.get("titulo", "")).strip() else None),
                "ubicacion_raw": normalizar_texto(item.get("municipio", None)),
                "zona_normalizada": normalizar_zona(item.get("municipio", None)),
                "habitaciones": pd.to_numeric(item.get("habitaciones", None), errors="coerce"),
                "banos": np.nan,
                "superficie_m2": None,
                "precio_original": price if price is not None else item.get("precio", None),
                "moneda": (str(item.get("moneda", "")).strip().upper() if pd.notna(item.get("moneda", None)) else None),
                "precio_sospechoso": suspicious,
                "fecha_publicacion": None,
                "fecha_descarga": pd.Timestamp.now().isoformat(timespec="seconds"),
                "garaje": None,
                "piscina": None,
                "terraza": None,
                "patio": None,
                "balcon": None,
                "jardin": None,
                "canal": "clasificado_informal",
                "agencia_observada": "desconocido",
                "sirve_proyecto": normalizar_texto(item.get("sirve_proyecto", None)),
                "calidad_metadatos": 0,
                "_required_fields": required,
                "texto_evidencia": normalizar_texto(item.get("texto_tarjeta", None)),
                "observacion": "Municipio/habitaciones derivados del titulo/formulario del extractor; texto_tarjeta puede contener varios anuncios y no se usa para variables individuales.",
            }
        )
    frame = pd.DataFrame(rows)
    frame["calidad_metadatos"] = frame.apply(lambda r: quality_score(r, required), axis=1)
    return frame[STANDARD_COLUMNS]


def dataframe_cubisima(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    rows = []
    required = ["tipo_vivienda", "ubicacion_raw", "habitaciones", "banos", "precio_original", "moneda"]
    feature_map = {
        "garaje": "garaje",
        "piscina": "piscina",
        "terraza": "terraza",
        "patio": "patio",
        "balcon": "balcon",
        "jardin": "jardin",
    }
    for idx, item in source.iterrows():
        price, suspicious = normalizar_precio(item.get("precio", None), item.get("moneda", None))
        ubi = normalizar_texto(item.get("zona", None))
        t = normalizar_texto(item.get("tipo", None))
        tipo = t.lower() if pd.notna(t) and t else None
        row = {
            "fuente": "Cubisima",
            "snapshot_origen": str(path.name),
            "id_local": f"cubisima_{idx + 1:06d}",
            "titulo": normalizar_texto(item.get("titulo", "")),
            "url": normalizar_texto(item.get("url", "")),
            "tipo_vivienda": tipo,
            "ubicacion_raw": ubi,
            "zona_normalizada": normalizar_zona(ubi),
            "habitaciones": pd.to_numeric(item.get("habitaciones", None), errors="coerce"),
            "banos": pd.to_numeric(item.get("banos", None), errors="coerce"),
            "superficie_m2": None,
            "precio_original": price if price is not None else item.get("precio", None),
            "moneda": (str(item.get("moneda", "")).strip().upper() if pd.notna(item.get("moneda", None)) else None),
            "precio_sospechoso": suspicious,
            "fecha_publicacion": normalizar_texto(item.get("fecha", None)),
            "fecha_descarga": pd.Timestamp.now().isoformat(timespec="seconds"),
            "canal": "plataforma_clasificados",
            "agencia_observada": "desconocido",
            "sirve_proyecto": None,
            "texto_evidencia": normalizar_texto(item.get("texto_tarjeta", None)),
            "observacion": "Precio recibido desde archivo local Cubisima; Cubisima se usa como fuente complementaria mas rica en banos y zona. Factores como garaje/piscina provienen de booleanos del extractor.",
        }
        for target, source_field in feature_map.items():
            raw = item.get(source_field, None)
            if pd.isna(raw):
                row[target] = None
            elif str(raw).strip().lower() in {"1", "true", "si", "sí", "yes"}:
                row[target] = 1
            elif str(raw).strip().lower() in {"0", "false", "no"}:
                row[target] = 0
            else:
                row[target] = pd.to_numeric(raw, errors="coerce")
        row["calidad_metadatos"] = quality_score(row, required)
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame[STANDARD_COLUMNS]


def dataframe_hogarencuba(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    rows = []
    required = ["tipo_vivienda", "ubicacion_raw", "habitaciones", "banos", "superficie_m2", "precio_original", "moneda"]
    feature_map = {"garaje": "garaje", "piscina": "piscina", "terraza": "terraza", "patio": "patio", "balcon": "balcon", "jardin": "jardin"}
    for idx, item in source.iterrows():
        price, suspicious = normalizar_precio(item.get("precio_original", None), item.get("moneda", None))
        if "precio_sospechoso" in source.columns and pd.notna(item.get("precio_sospechoso", None)):
            suspicious = str(item.get("precio_sospechoso")).strip().lower().replace("Ã­", "i") in {"true", "1", "si", "yes"}
        row = {
            "fuente": "HogarEnCuba",
            "snapshot_origen": str(path.name),
            "id_local": (str(item.get("id_local", "")).strip() or f"hec_{idx + 1:06d}"),
            "titulo": normalizar_texto(item.get("titulo", "")),
            "url": normalizar_texto(item.get("url", "")),
            "tipo_vivienda": normalizar_texto(item.get("tipo_vivienda", None)),
            "ubicacion_raw": normalizar_texto(item.get("ubicacion_raw", None)),
            "zona_normalizada": normalizar_zona(item.get("ubicacion_raw", None)),
            "habitaciones": pd.to_numeric(item.get("habitaciones", None), errors="coerce"),
            "banos": pd.to_numeric(item.get("banos", None), errors="coerce"),
            "superficie_m2": pd.to_numeric(item.get("superficie_m2", None), errors="coerce"),
            "precio_original": price if price is not None else item.get("precio_original", None),
            "moneda": (str(item.get("moneda", "")).strip().upper() if pd.notna(item.get("moneda", None)) else None),
            "precio_sospechoso": suspicious,
            "fecha_publicacion": normalizar_texto(item.get("fecha_publicacion", None)),
            "fecha_descarga": pd.Timestamp.now().isoformat(timespec="seconds"),
            "garaje": pd.to_numeric(item.get("garaje", None), errors="coerce"),
            "piscina": pd.to_numeric(item.get("piscina", None), errors="coerce"),
            "terraza": pd.to_numeric(item.get("terraza", None), errors="coerce"),
            "patio": pd.to_numeric(item.get("patio", None), errors="coerce"),
            "balcon": pd.to_numeric(item.get("balcon", None), errors="coerce"),
            "jardin": pd.to_numeric(item.get("jardin", None), errors="coerce"),
            "canal": normalizar_texto(item.get("canal", None)) or "plataforma_estructurada",
            "agencia_observada": normalizar_texto(item.get("agencia_observada", None)) or "no verificado (plataforma individual)",
            "sirve_proyecto": None,
            "texto_evidencia": normalizar_texto(item.get("texto_evidencia", None)),
            "observacion": "Fuente formal/estructurada con m2, banos y municipio; los anuncios se parsean desde fichas individuales.",
        }
        row["calidad_metadatos"] = quality_score(row, required)
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame[STANDARD_COLUMNS]



def integrar(dedup_by_url: bool = True) -> pd.DataFrame:
    root = REPO_ROOT
    revolico_path = root / "anuncios_revolico_procesados.csv"
    cubisima_path = root / "viviendas_cubisima.csv"
    hogar_dir = root / "outputs" / "hogarencuba"
    if hogar_dir.exists():
        hogar_candidates = []
        for candidate in hogar_dir.glob("viviendas_hogarencuba_*.csv"):
            try:
                if candidate.stat().st_size > 0 and len(pd.read_csv(candidate, dtype=str)) > 0:
                    hogar_candidates.append(candidate)
            except Exception:
                continue
        if hogar_candidates:
            hogar_scores = [(p, len(pd.read_csv(p, dtype=str))) for p in hogar_candidates]
            hogar_path = max(hogar_scores, key=lambda x: (x[1], x[0].name))[0]
        else:
            hogar_path = None
    else:
        hogar_path = None
        hogar_path = None

    if not revolico_path.exists():
        raise FileNotFoundError(revolico_path)
    if not cubisima_path.exists():
        raise FileNotFoundError(cubisima_path)

    rev = dataframe_revolico(revolico_path)
    cub = dataframe_cubisima(cubisima_path)
    frames = [rev, cub]
    if hogar_path is not None:
        hog = dataframe_hogarencuba(hogar_path)
        frames.append(hog)
    merged = pd.concat(frames, ignore_index=True)

    if dedup_by_url:
        merged["_quality_key"] = merged["calidad_metadatos"].fillna(0).astype(int)
        # Mantener el registro con mas metadatos cuando una URL coincide.
        merged = merged.sort_values("_quality_key", ascending=False).drop_duplicates(subset=["url"], keep="first")
        merged = merged.drop(columns=["_quality_key"])

    merged = merged.sort_values(["fuente", "id_local"], kind="stable").reset_index(drop=True)
    merged["id_maestro"] = [f"maestro_{i:06d}" for i in range(1, len(merged) + 1)]
    # Poner id_maestro primero para facilitar futuras uniones.
    columns = ["id_maestro"] + STANDARD_COLUMNS
    return merged[columns]


def main():
    parser = argparse.ArgumentParser(description="Integracion no destructiva de fuentes inmobiliarias cubanas")
    parser.add_argument("--sin-dedup", action="store_true", help="No deduplicar por URL.")
    args = parser.parse_args()

    frame = integrar(dedup_by_url=not args.sin_dedup)
    out_dir = REPO_ROOT / "outputs" / "integracion"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = out_dir / f"dataset_maestro_20261015_{stamp.split('_')[-1]}.csv"
    # Usar un nombre claro y reproducible con fecha+hora.
    output = out_dir / f"dataset_maestro_{stamp}.csv"
    frame.to_csv(output, index=False, encoding="utf-8-sig")

    summary = frame.groupby(["fuente", "moneda", "canal"], dropna=False).agg(
        anuncios=("id_maestro", "count"),
        banos_disponibles=("banos", lambda s: int(pd.notna(s).sum())),
        habitaciones_disponibles=("habitaciones", lambda s: int(pd.notna(s).sum())),
        precio_sospechoso=("precio_sospechoso", lambda s: int(pd.notna(s).sum())),
    ).reset_index()
    summary_path = out_dir / f"resumen_integracion_{stamp}.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"Dataset maestro: {output}")
    print(f"Filas: {len(frame)}")
    print(f"Salida resumen: {summary_path}")
    print("\nPor fuente:")
    print(frame.groupby("fuente").size().to_string())
    print("\nMoneda:")
    print(frame["moneda"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()