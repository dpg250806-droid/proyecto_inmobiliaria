#!/usr/bin/env python3
"""Genera graficas, tablas y un esquema del proyecto inmobiliario cubano."""
from __future__ import annotations

from pathlib import Path
import re
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

from precio_moneda import normalizar_moneda

ROOT = Path(__file__).resolve().parent
MASTER_GLOB = "outputs/integracion/dataset_maestro_*.csv"
OUT = ROOT / "outputs" / "visualizaciones"
OUT.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 130
plt.rcParams["savefig.bbox"] = "tight"


def newest_master() -> Path:
    files = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))
    if not files:
        raise FileNotFoundError("No hay dataset maestro. Ejecuta primero integrar_fuentes.py")
    return files[-1]


def money_labels(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    frame.loc[frame["moneda"].eq("CUP"), "precio_original"] = pd.to_numeric(
        frame.loc[frame["moneda"].eq("CUP"), "precio_original"], errors="coerce"
    )
    return frame


def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)
    return path


def plot_price_distribution(frame: pd.DataFrame):
    subset = frame[
        frame["precio_original"].notna()
        & frame["precio_original"].gt(0)
        & frame["moneda"].astype(str).str.strip().ne("")
    ].copy()
    subset = subset[~subset["precio_sospechoso"].fillna(False).astype(bool)]
    if subset.empty:
        return None
    currencies = ["USD", "EUR", "CUC", "CUP"]
    fig, axes = plt.subplots(len(currencies), 1, figsize=(10, 8), sharex=False)
    any_plot = False
    for ax, currency in zip(axes, currencies):
        data = subset[subset["moneda"].astype(str).str.upper().eq(currency)]
        if data.empty:
            ax.text(0.5, 0.5, f"Sin datos {currency}", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            continue
        any_plot = True
        capq = data["precio_original"].quantile(0.98)
        data = data[data["precio_original"].le(capq)]
        sns.histplot(
            data=data,
            x="precio_original",
            hue="fuente",
            kde=data["precio_original"].nunique() > 1,
            ax=ax,
            element="step",
            stat="density",
        )
        ax.set_title(f"Precio publicado ({currency}) por fuente")
        ax.set_xlabel(f"Precio ({currency})")
        ax.set_ylabel("Densidad")
    if not any_plot:
        plt.close(fig)
        return None
    path = save(fig, "01_distribucion_precios_por_moneda.png")
    return path


def plot_municipality_median(frame: pd.DataFrame):
    subset = frame[
        frame["ubicacion_raw"].notna()
        & frame["precio_original"].notna()
        & frame["moneda"].astype(str).str.strip().ne("")
    ].copy()
    subset = subset[~subset["precio_sospechoso"].fillna(False).astype(bool)]
    if subset.empty:
        return None
    # Normalizar binario de municipio.
    subset["municipio_grafico"] = subset["ubicacion_raw"].astype(str).str.strip().str.title()
    counts = subset.groupby(["moneda", "municipio_grafico"]).size()
    usable = counts[counts.ge(10)].index
    subset = subset.set_index(["moneda", "municipio_grafico"]).loc[lambda x: x.index.isin(usable)].reset_index()
    if subset.empty:
        return None
    med = subset.groupby(["moneda", "municipio_grafico"]).agg(
        mediana=("precio_original", "median"),
        n=("precio_original", "count"),
    ).reset_index()
    graph = sns.catplot(
        data=med,
        x="mediana",
        y="municipio_grafico",
        col="moneda",
        col_wrap=2,
        kind="bar",
        sharex=False,
        color="#4472c4",
        height=max(4, 0.3 * med["municipio_grafico"].nunique()),
        aspect=1.4,
    )
    graph.set_axis_labels("Precio mediano", "Municipio/zona")
    graph.set_titles("Moneda: {col_name}")
    graph.fig.suptitle("Precio mediano por municipio/zona, separado por moneda (n ≥ 10)", y=1.02)
    path = OUT / "02_mediana_precio_por_municipio.png"
    graph.fig.savefig(path, dpi=140, facecolor="white")
    plt.close(graph.fig)
    return path


def plot_rooms_price(frame: pd.DataFrame):
    subset = frame[
        frame["habitaciones"].notna()
        & frame["precio_original"].notna()
        & frame["moneda"].astype(str).str.strip().ne("")
    ].copy()
    subset = subset[~subset["precio_sospechoso"].fillna(False).astype(bool)]
    if subset.empty:
        return None
    subset["habitaciones"] = subset["habitaciones"].clip(1, 8).astype(int).astype(str)
    order = sorted(subset["habitaciones"].unique(), key=lambda x: int(x))
    g = sns.catplot(data=subset, x="habitaciones", y="precio_original", hue="fuente",
                    col="moneda", kind="box", height=4.8, aspect=1.05, order=order,
                    showfliers=False)
    g.set_axis_labels("Habitaciones (agrupadas)", "Precio original")
    g.set_titles("{col_name}")
    path = save(g.figure, "03_habitaciones_precio_por_moneda.png")
    return path


def plot_feature_frequency(frame: pd.DataFrame):
    feature_cols = ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]
    means = {}
    for col in feature_cols:
        if col in frame.columns:
            series = pd.to_numeric(frame.loc[frame["fuente"].eq("Cubisima"), col], errors="coerce")
            if series.notna().any():
                means[col] = float(series.fillna(0).mean())
    if not means:
        return None
    features = sorted(means, key=means.get, reverse=True)
    values = [means[f] * 100 for f in features]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(features, values, color="#70ad47")
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=2, fontsize=8)
    ax.set_xlabel("% de anuncios Cubisima con la característica")
    ax.set_ylabel("Característica")
    ax.set_title("Frecuencia de características auxiliares en Cubisima")
    path = save(fig, "04_frecuencia_caracteristicas_cubisima.png")
    return path


def plot_metadata_quality(frame: pd.DataFrame):
    fields = ["ubicacion_raw", "habitaciones", "banos", "precio_original", "moneda", "fecha_publicacion"]
    rows = []
    for source, g in frame.groupby("fuente"):
        for field in fields:
            if field == "moneda" and field in g:
                coverage = float(g[field].ne("").mean())
            else:
                coverage = float(pd.notna(g[field]).mean()) if field in g else 0
            rows.append({
                "fuente": source,
                "campo": field,
                "cobertura_pct": 100 * coverage,
            })
    q = pd.DataFrame(rows)
    if q.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5.2))
    sns.barplot(data=q, x="campo", y="cobertura_pct", hue="fuente", ax=ax)
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Campo")
    ax.set_title("Calidad de metadatos por fuente")
    ax.set_ylim(0, 100)
    path = save(fig, "05_calidad_metadatos_fuentes.png")
    return path


def plot_exchange_rates():
    path_file = ROOT / "data" / "tasas"
    rate_files = sorted(path_file.glob("tasas_cambio_*.csv")) if path_file.exists() else []
    if not rate_files:
        return None, None
    r = pd.read_csv(rate_files[-1])
    long_rows = []
    for col_stem, label in [("usd_informal_cup", "USD informal"), ("usd_formal_cup", "USD formal"),
                      ("eur_informal_cup", "EUR informal"), ("eur_formal_cup", "EUR formal")]:
        if col_stem in r.columns and pd.notna(r[col_stem]).any():
            long_rows.append({"moneda": label, "cup_por_unidad": float(r[col_stem].iloc[0])})
    rates = pd.DataFrame(long_rows)
    if rates.empty:
        return None, rate_files[-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#bf8f00", "#f4c20d", "#4472c4", "#9bc2e6"]
    bars = ax.bar(rates["moneda"], rates["cup_por_unidad"], color=colors[:len(rates)])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in rates["cup_por_unidad"]], padding=2, fontsize=8)
    ax.set_ylabel("CUP por unidad")
    ax.set_title("Tasas USD/EUR -> CUP guardadas")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    path = save(fig, "06_tasas_usd_eur_cup.png")
    return path, rate_files[-1]


def plot_schema():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    boxes = [
        (0.3, 7.8, 2.0, 1.1, "Fuentes\nRevolico / Cubisima /\n Casas Oasis", "#dbe5ff"),
        (3.2, 7.8, 2.2, 1.1, "Extraccion no destructiva\npreserva CSV originales", "#d9f2d9"),
        (6.2, 7.8, 2.0, 1.1, "Dataset maestro\nid_maestro + trazabilidad", "#f7e2bd"),
        (0.3, 4.8, 9.0, 1.4, "Variables clave: precio, moneda, ubicacion, habitaciones, banos, fecha, canal, calidad de metadatos", "#f2d9ff"),
        (0.3, 2.4, 4.2, 1.4, "Tasas\ninformal de ElToque\nformal institucional\n registro manual si falla", "#fce4d6"),
        (5.1, 2.4, 4.2, 1.4, "Analisis\nEDA, clustering futuro,\n entrevistas trianguladas", "#d9eaf7"),
        (0.3, 0.1, 9.0, 1.6, "Salidas\ngraficas PNG, tablas CSV/MD,\n README y commits reproducibles", "#e2e2e2"),
    ]
    for x, y, w, h, text, color in boxes:
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06", linewidth=1.5, edgecolor="#555", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10, weight="bold")

    # Arrows
    arrow_kwargs = {"arrowstyle": "->", "lw": 2.0, "color": "#404040", "connectionstyle": "arc3,rad=0"}
    ax.annotate("", xy=(3.2, 8.35), xytext=(2.3, 8.35), arrowprops=arrow_kwargs)
    ax.annotate("", xy=(6.2, 8.35), xytext=(5.4, 8.35), arrowprops=arrow_kwargs)
    ax.annotate("", xy=(4.8, 6.2), xytext=(4.8, 7.8), arrowprops=arrow_kwargs)
    ax.annotate("", xy=(2.4, 3.8), xytext=(4.8, 6.2), arrowprops=arrow_kwargs)
    ax.annotate("", xy=(7.2, 3.8), xytext=(4.8, 6.2), arrowprops=arrow_kwargs)
    ax.annotate("", xy=(4.8, 1.7), xytext=(4.8, 2.4), arrowprops=arrow_kwargs)
    ax.set_title("Esquema de integracion y analisis inmobiliario", fontsize=14, weight="bold")
    path = save(fig, "07_esquema_integracion.png")
    return path


def write_summary(frame: pd.DataFrame, paths: dict):
    lines = []
    lines.append("# Resumen visual y tabular de fuentes")
    lines.append("")
    lines.append(f"Dataset maestro mas reciente: `{newest_master().name}`")
    lines.append("")
    lines.append("## Filas y calidad")
    counts = frame.groupby("fuente").agg(
        anuncios=("id_maestro", "count"),
        precio=("precio_original", lambda s: pd.notna(s).sum()),
        municipio_zona=("ubicacion_raw", lambda s: pd.notna(s).sum()),
        habitaciones=("habitaciones", lambda s: pd.notna(s).sum()),
        banos=("banos", lambda s: pd.notna(s).sum()),
    )
    lines.append(counts.to_markdown())
    lines.append("")
    lines.append("## Precio central por fuente y moneda")
    usable = frame[
        frame["precio_original"].notna()
        & frame["moneda"].ne("")
        & ~frame["precio_sospechoso"].fillna(False).astype(bool)
    ]
    stats = usable.groupby(["fuente", "moneda"])["precio_original"].agg(["count", "median", "mean", "min", "max"]).reset_index()
    lines.append(stats.to_markdown(index=False))
    lines.append("")
    lines.append("## Habitaciones vs precio en Cubisima")
    cub = usable[usable["fuente"].eq("Cubisima") & usable["habitaciones"].notna()]
    if not cub.empty:
        hab_stats = cub.groupby(["moneda", "habitaciones"])["precio_original"].agg(["count", "median", "mean"]).round(2)
        lines.append(hab_stats.to_markdown())
    else:
        lines.append("Sin datos suficientes.")
    lines.append("")
    lines.append("## Caracteristicas mas frecuentes en Cubisima")
    feats = ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]
    lines.extend([f"- **{f}**: {pd.to_numeric(frame.loc[frame['fuente'].eq('Cubisima'), f], errors='coerce').fillna(0).astype(int).sum()} anuncios" for f in feats if f in frame.columns])
    lines.append("")
    lines.append("## Gráficos generados")
    for name, p in paths.items():
        if p:
            lines.append(f"- `{p.name}`")
    lines.append("")
    lines.append("## Nota metodológica")
    lines.append("Los precios originales se resumen por fuente y moneda; los gráficos de precio separan monedas. No se comparan directamente importes de monedas distintas.")
    path = OUT / "visualizaciones_resumen.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    frame = pd.read_csv(newest_master(), dtype=str)
    # Normalizar campos numericos.
    for col in ["precio_original", "habitaciones", "banos"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["precio_sospechoso"] = frame["precio_sospechoso"].astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False})
    frame["fecha_descarga"] = pd.to_datetime(frame["fecha_descarga"], errors="coerce")
    frame = money_labels(frame)

    paths = {}
    paths["distribucion"] = plot_price_distribution(frame)
    paths["municipio"] = plot_municipality_median(frame)
    paths["habitaciones"] = plot_rooms_price(frame)
    paths["caracteristicas"] = plot_feature_frequency(frame)
    paths["calidad"] = plot_metadata_quality(frame)
    p, rate_file = plot_exchange_rates()
    paths["tasas"] = p
    paths["esquema"] = plot_schema()
    summary = write_summary(frame, paths)
    if rate_file:
        print(f"Tasa reciente usada como fuente: {rate_file}")
    print(f"Resumen escrito en: {summary}")
    for name, p in paths.items():
        if p:
            print(f"Imagen guardada: {p}")


if __name__ == "__main__":
    main()