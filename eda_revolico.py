#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EDA reproducible y read-only del dataset Revolico.

Genera un informe Markdown en outputs/eda/. No modifica los CSV de entrada.
Los graficos quedan pendientes de instalar librerias de visualizacion si el
usuario lo autoriza.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "anuncios_revolico_procesados.csv"


def fmt_tabla(filas: list[dict]) -> str:
    if not filas:
        return "_Sin datos._\n"
    columnas = list(filas[0].keys())
    salida = ["| " + " | ".join(columnas) + " |", "| " + " | ".join(["---"] * len(columnas)) + " |"]
    for fila in filas:
        salida.append("| " + " | ".join(str(fila[c]) for c in columnas) + " |")
    return "\n".join(salida) + "\n"


def principal() -> None:
    if not ENTRADA.exists():
        raise FileNotFoundError(f"No existe {ENTRADA}")

    df = pd.read_csv(ENTRADA)
    salida_dir = RAIZ / "outputs" / "eda"
    salida_dir.mkdir(parents=True, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte = salida_dir / f"eda_revolico_{sello}.md"

    precio = pd.to_numeric(df["precio"], errors="coerce")
    habitaciones = pd.to_numeric(df["habitaciones"], errors="coerce")
    municipio = df["municipio"]

    lineas = []
    lineas.append("# EDA reproducible: mercado inmobiliario Revolico (La Habana)")
    lineas.append("")
    lineas.append(f"- Fecha y hora: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lineas.append(f"- Entrada: `{ENTRADA.name}` (no modificada)")
    lineas.append(f"- Filas: {len(df)}")
    lineas.append("- Fuente: 8 paginas HTML manuales de Revolico descargadas localmente.")
    lineas.append("")

    lineas.append("## 1. Clasificacion")
    lineas.append("")
    lineas.append(fmt_tabla([{"sirve_proyecto": k, "cantidad": v} for k, v in df["sirve_proyecto"].value_counts().items()]))

    lineas.append("## 2. Datos ausentes")
    lineas.append("")
    lineas.append(fmt_tabla([{"columna": c, "ausentes": int(df[c].isna().sum()), "porcentaje": f"{df[c].isna().mean() * 100:.2f}%"} for c in df.columns]))

    lineas.append("## 3. Tipo de vivienda detectado en titulo")
    lineas.append("")
    tipo = df["titulo"].fillna("").astype(str).str.lower()
    conteo_tipo = []
    conteo_tipo.append({"tipo_detectado": "casa", "cantidad": int(tipo.str.contains(r"\bcasa\b", regex=True).sum())})
    conteo_tipo.append({"tipo_detectado": "apartamento/apt", "cantidad": int(tipo.str.contains("apart|apto", regex=True).sum())})
    conteo_tipo.append({"tipo_detectado": "penthouse", "cantidad": int(tipo.str.contains("penthouse", regex=False).sum())})
    lineas.append(fmt_tabla(conteo_tipo))

    lineas.append("## 4. Cobertura territorial")
    lineas.append("")
    lineas.append(f"- Municipios disponibles: {municipio.notna().sum()} ({municipio.notna().mean() * 100:.2f}%)")
    lineas.append(f"- Municipios ausentes: {municipio.isna().sum()} ({municipio.isna().mean() * 100:.2f}%)")
    lineas.append("")
    lineas.append(fmt_tabla([{"municipio": k, "cantidad": v} for k, v in municipio.value_counts(dropna=False).head(20).items()]))

    lineas.append("## 5. Precios")
    lineas.append("")
    lineas.append(fmt_tabla([{"indicador": k, "valor": (f"{v:,.2f}" if isinstance(v, float) else v)} for k, v in [
        ("observaciones con precio", int(precio.notna().sum())),
        ("precio minimo", float(precio.min())),
        ("percentil 25", float(precio.quantile(0.25))),
        ("mediana", float(precio.median())),
        ("percentil 75", float(precio.quantile(0.75))),
        ("precio maximo", float(precio.max())),
        ("media", float(precio.mean())),
        ("desviacion estandar", float(precio.std())),
    ]]))
    lineas.append("")
    lineas.append("Distribucion por moneda:")
    lineas.append("")
    lineas.append(fmt_tabla([{"moneda": (str(k) if pd.notna(k) else "NA"), "cantidad": int(v)} for k, v in df["moneda"].value_counts(dropna=False).items()]))
    lineas.append("")
    lineas.append("Precios sospechosos:")
    lineas.append("")
    lineas.append(f"- Precio < 100: {int(precio.lt(100).sum())}")
    lineas.append(f"- Precio > 100000: {int(precio.gt(100000).sum())}")
    lineas.append(f"- Precio igual a 1: {int(precio.eq(1).sum())}")
    lineas.append("")

    lineas.append("## 6. Habitaciones")
    lineas.append("")
    lineas.append(f"- Disponibles: {int(habitaciones.notna().sum())} ({habitaciones.notna().mean() * 100:.2f}%)")
    lineas.append(f"- Ausentes: {int(habitaciones.isna().sum())} ({habitaciones.isna().mean() * 100:.2f}%)")
    lineas.append("")
    lineas.append(fmt_tabla([{"habitaciones": f"{k:g}", "cantidad": int(v)} for k, v in habitaciones.value_counts(dropna=True).sort_index().items()]))
    lineas.append("")

    lineas.append("## 7. Relacion precio-habitaciones (solo datos disponibles)")
    lineas.append("")
    subset = df[["precio", "habitaciones"]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(subset) >= 3:
        correlacion = subset["precio"].corr(subset["habitaciones"])
        lineas.append(f"- Observaciones usables: {len(subset)}")
        lineas.append(f"- Correlacion de Pearson precio-habitaciones: {correlacion:.4f}")
    else:
        lineas.append("No hay suficientes observaciones para calcular la correlacion.")
    lineas.append("")

    lineas.append("## 8. Duplicados")
    lineas.append("")
    normal = df["titulo"].fillna("").astype(str).str.strip().str.lower()
    lineas.append(f"- Titulos exactamente duplicados: {int(df['titulo'].duplicated().sum())}")
    lineas.append(f"- Titulos duplicados tras normalizacion: {int(normal.duplicated().sum())}")
    lineas.append(f"- URLs duplicadas: {int(df['url'].duplicated().sum())}")
    lineas.append("")

    lineas.append("## 9. Limitaciones para el analisis")
    lineas.append("")
    lineas.append("- El municipio y las habitaciones se infieren solo del titulo, con ausencia alta.")
    lineas.append("- El precio se infiere del numero inicial del titulo y puede incluir telefonos o montos no monetarios.")
    lineas.append("- `texto_tarjeta` esta contaminado por contenedores compartidos.")
    lineas.append("- `datos_revolico_json.csv` no representa exclusivamente viviendas.")
    lineas.append("- No se han incluido graficos en esta etapa porque no hay librerias de visualizacion instaladas.")
    lineas.append("")

    lineas.append("## 10. Variables candidatas para una futura etapa")
    lineas.append("")
    lineas.append("- precio validado o marcado sospechoso;")
    lineas.append("- municipio normalizado;")
    lineas.append("- tipo de vivienda (casa/apartamento);")
    lineas.append("- habitaciones cuando esten disponibles;")
    lineas.append("- moneda;");
    lineas.append("- texto o metadatos adicionales desde otras fuentes cubanas (Cubisima, Casas Oasis, HogarEnCuba).")
    lineas.append("")

    reporte.write_text("\n".join(lineas), encoding="utf-8")
    print(f"EDA guardado en: {reporte}")


if __name__ == "__main__":
    principal()
