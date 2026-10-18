#!/usr/bin/env python3
"""Revalida precios discordantes de un snapshot HogarEnCuba sin sobrescribirlo."""
from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from bs4 import BeautifulSoup

from scraper_hogarencuba import fetch, parse_detail


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "outputs" / "hogarencuba"
OUTPUT_DIR = INPUT_DIR
REQUIRED_COLUMNS = {"id_local", "url", "titulo", "precio_original", "moneda", "texto_evidencia"}


def _same_price(left, right) -> bool:
    old = pd.to_numeric(left, errors="coerce")
    new = pd.to_numeric(right, errors="coerce")
    return (pd.isna(old) and pd.isna(new)) or (pd.notna(old) and pd.notna(new) and float(old) == float(new))


def _currency(value):
    if pd.isna(value):
        return None
    normalized = str(value).strip().upper()
    return None if normalized in {"", "NAN", "NONE", "<NA>"} else normalized


def revalidar(
    source: Path,
    output: Path,
    delay: float = 1.0,
    fetcher=fetch,
) -> tuple[int, int]:
    if source.resolve() == output.resolve():
        raise ValueError("La salida no puede sobrescribir el snapshot de origen.")
    if delay < 0:
        raise ValueError("delay no puede ser negativo.")

    frame = pd.read_csv(source, dtype=str, encoding="utf-8-sig")
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas necesarias en {source}: {', '.join(sorted(missing))}")

    for column in (
        "precio_previo_revalidacion",
        "moneda_previa_revalidacion",
        "precio_metodo_extraccion",
        "precio_evidencia",
        "revalidacion_estado",
    ):
        if column not in frame:
            frame[column] = ""

    for index, row in frame.iterrows():
        frame.at[index, "precio_previo_revalidacion"] = row.get("precio_original", "")
        frame.at[index, "moneda_previa_revalidacion"] = row.get("moneda", "")
        offline = parse_detail(row.get("texto_evidencia") or "", row.get("titulo") or "", row.get("url") or "")
        if _same_price(row.get("precio_original"), offline["precio_original"]) and (
            _currency(row.get("moneda")) == offline["moneda"]
        ):
            frame.at[index, "revalidacion_estado"] = "sin_discrepancia_en_evidencia_local"
            continue

        url = row.get("url") or ""
        if urlparse(url).netloc.lower() != "hogarencuba.com":
            raise ValueError(f"URL fuera del dominio esperado para {row.get('id_local')}: {url}")
        html = fetcher(url)
        detail_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        current = parse_detail(detail_text, row.get("titulo") or "", url, html)
        frame.at[index, "precio_original"] = (
            "" if current["precio_original"] is None else str(current["precio_original"])
        )
        frame.at[index, "moneda"] = current["moneda"] or ""
        frame.at[index, "precio_metodo_extraccion"] = current["precio_metodo_extraccion"]
        frame.at[index, "precio_evidencia"] = current["precio_evidencia"]
        frame.at[index, "revalidacion_estado"] = "revalidado_live"
        if delay:
            time.sleep(delay)

    revalidated = int(frame["revalidacion_estado"].eq("revalidado_live").sum())
    frame["revalidaciones_live_total"] = revalidated
    frame["snapshot_origen_revalidacion"] = source.name

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8-sig", newline="") as handle:
        frame.to_csv(handle, index=False)
    return len(frame), revalidated


def latest_source(directory: Path) -> Path:
    candidates = []
    for path in directory.glob("viviendas_hogarencuba_*.csv"):
        try:
            row_count = len(pd.read_csv(path, dtype=str, encoding="utf-8-sig"))
            if row_count:
                candidates.append((row_count, path.stat().st_mtime, path))
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
            continue
    if not candidates:
        raise FileNotFoundError(f"No hay snapshots revisados en {directory}")
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Snapshot revisado de HogarEnCuba.")
    parser.add_argument("--output", type=Path, help="Archivo de salida nuevo; nunca se sobrescribe.")
    parser.add_argument("--delay", type=float, default=1.0, help="Espera entre anuncios revalidados.")
    args = parser.parse_args()
    source = args.input or latest_source(INPUT_DIR)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or OUTPUT_DIR / f"viviendas_hogarencuba_revalidada_{stamp}.csv"
    total, revalidated = revalidar(source, output, delay=args.delay)
    print(f"Snapshot nuevo: {output}")
    print(f"Filas preservadas: {total}; precios/monedas revalidados en vivo: {revalidated}")
    print(f"Snapshot de origen sin cambios: {source}")


if __name__ == "__main__":
    main()
