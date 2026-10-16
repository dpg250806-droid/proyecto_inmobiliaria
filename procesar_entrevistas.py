#!/usr/bin/env python3
"""Procesa anonimamente entrevistas exportadas desde Google Forms."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd

QUESTIONS = {
    "Cuál es su relación con la vivienda?": "relacion",
    "En qué municipio se encuentra la vivienda con la que tiene mayor conocimiento?": "municipio",
    "En su opinión, ¿cómo han evolucionado los precios de las viviendas en Cuba desde 2020 hasta la actualidad? ¿A qué atribuye esos cambios?": "evolucion_precios",
    "¿Cuáles considera que son los principales factores que  determinan el precio de una vivienda en Cuba?": "factores_precio",
    "¿Qué influencia cree que tienen el USD, el EUR y las tasas de cambio oficiales e informales en la fijación de los precios de las viviendas?": "influencia_tasas",
    "¿Considera que los precios publicados en los anuncios inmobiliarios reflejan el valor real de las viviendas? ¿Por qué?": "refleja_precio",
    "¿Qué influencia considera que ha tenido la migración en la oferta, la demanda y los precios de las viviendas en Cuba durante el período del 2020 hasta el año actual?": "influencia_migracion",
    "Entre la crisis económica, las variaciones de las tasas de cambio y la migración, ¿cuál considera que ha influido más en el mercado inmobiliario cubano? ¿Por qué?": "factor_dominante",
    "¿Qué factores podrían llevar a una persona a reducir el precio solicitado por su vivienda o dificultar su venta?": "reduccion_precio",
    "¿Qué canales considera más efectivos para ofertar viviendas en Cuba y qué información debería incluir un anuncio para generar confianza?": "canales",
}


def normalized_texts(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    cols = [c for c in frame.columns if c != "Marca temporal"]
    for col in cols:
        frame[col] = frame[col].astype(str).str.replace("\n", " ").str.strip()
    return frame


def code_row(row: pd.Series) -> dict:
    all_text = " ".join(str(x) for x in row if isinstance(x, str)).lower()
    codes = {
        "C1_necesidad_economica": int("dinero" in all_text or "necesidad" in all_text or "urgencia" in all_text or "misera" in all_text),
        "C2_migracion": int("migra" in all_text or "travesia" in all_text or "nicaragua" in all_text),
        "C3_moneda_tasa": int("usd" in all_text or "cup" in all_text or "tasas" in all_text or "moneda" in all_text),
        "C4_canal_venta": int("telegram" in all_text or "whatsapp" in all_text or "facebook" in all_text or "grupo" in all_text),
        "C5_precio_alto": int("caro" in all_text or "carisimo" in all_text or "regalo" in all_text or "valor" in all_text),
        "C6_caracteristicas": int("m2" in all_text or "metro" in all_text or "baño" in all_text or "baños" in all_text or "piscina" in all_text),
        "C7_municipio": int("playa" in all_text or "cerro" in all_text or "cerro" in all_text or "plaza" in all_text),
        "A1_cita": all_text[:220],
    }
    return codes


def main():
    parser = argparse.ArgumentParser(description="Procesa entrevistas anonimas de Google Forms")
    parser.add_argument("--csv", required=True, help="Ruta al CSV exportado")
    parser.add_argument("--outdir", default="outputs/entrevistas", help="Carpeta de salida")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(args.csv, dtype=str)
    if "Marca temporal" in raw.columns:
        raw = raw.rename(columns={"Marca temporal": "fecha_respuesta"})
    frame = normalized_texts(raw)
    frame = frame.rename(columns=QUESTIONS)
    frame.insert(0, "entrevista_id", [f"E{i:02d}" for i in range(1, len(frame) + 1)])

    code_rows = frame.apply(code_row, axis=1)
    code_frame = pd.DataFrame(list(code_rows))
    coded = pd.concat([frame, code_frame], axis=1)

    csv_path = outdir / f"entrevistas_codificadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    coded.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = []
    summary.append("# Resumen de entrevistas")
    summary.append(f"- Respuestas: {len(coded)}")
    summary.append(f"- Columnas: {', '.join(coded.columns)}")
    summary.append("")
    summary.append("## Frecuencia de codigos")
    for code in [c for c in code_frame.columns if c.startswith("C")]:
        summary.append(f"- {code}: {int(code_frame[code].sum())}")
    summary.append("")
    summary.append("## Relacion/municipio")
    if "relacion" in coded and "municipio" in coded:
        summary.append(coded.groupby(["relacion", "municipio"]).size().to_string())
    summary.append("")
    summary.append("## Citas ilustrativas")
    for idx, row in coded.iterrows():
        summary.append(f"- **{row['entrevista_id']}**: {row['A1_cita']}")
    summary_path = outdir / f"resumen_entrevistas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    summary_path.write_text("\n".join(summary), encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"Resumen: {summary_path}")
    print("Criterios de codificacion:")
    for code in [c for c in code_frame.columns if c.startswith("C")]:
        print(f"  {code}: {int(code_frame[code].sum())}")


if __name__ == "__main__":
    main()