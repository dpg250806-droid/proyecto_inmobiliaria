#!/usr/bin/env python3
"""Crea una copia corregida del CSV local de Cubisima sin alterar el original."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from precio_moneda import extraer_precio_moneda


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "viviendas_cubisima.csv"
OUTPUT_DIR = ROOT / "outputs" / "cubisima"


def reprocesar(source: Path, output: Path) -> int:
    if source.resolve() == output.resolve():
        raise ValueError("La salida no puede sobrescribir el CSV original.")

    with source.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"texto_tarjeta", "url", "precio", "moneda"} <= set(reader.fieldnames):
            raise ValueError(f"El CSV no contiene las columnas requeridas: {source}")
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    audit_fields = [
        "precio_previo_reprocesamiento",
        "moneda_previa_reprocesamiento",
        "moneda_original_previa_reprocesamiento",
        "reprocesamiento_estado",
    ]
    output_fields = fieldnames + [field for field in audit_fields if field not in fieldnames]
    for row in rows:
        row["precio_previo_reprocesamiento"] = row.get("precio", "")
        row["moneda_previa_reprocesamiento"] = row.get("moneda", "")
        row["moneda_original_previa_reprocesamiento"] = row.get("moneda_original", "")
        price, currency = extraer_precio_moneda(row.get("texto_tarjeta", ""), row.get("url", ""))
        if price is not None:
            row["precio"] = str(price)
        row["moneda"] = currency or ""
        if "moneda_original" in row:
            row["moneda_original"] = currency or ""
        row["reprocesamiento_estado"] = (
            "extraido"
            if price is not None and currency is not None
            else "moneda_no_identificada"
            if price is not None
            else "sin_precio"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=SOURCE, help="CSV guardado de Cubisima.")
    parser.add_argument("--output", type=Path, help="Destino nuevo; nunca se sobrescriben archivos.")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or OUTPUT_DIR / f"viviendas_cubisima_reprocesada_{stamp}.csv"
    count = reprocesar(args.input, output)
    print(f"Copia corregida creada: {output}")
    print(f"Anuncios procesados: {count}")
    print(f"CSV original intacto: {args.input}")
    print("El dataset maestro existente no cambia; reconstruyelo con python integrar_fuentes.py.")


if __name__ == "__main__":
    main()
