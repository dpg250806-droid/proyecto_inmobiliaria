#!/usr/bin/env python3
"""Tablas y graficas para comparar fuentes/canales y cobertura."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "outputs" / "comparativos"

FEATURES = ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]


def newest_master() -> Path:
    files = sorted(MASTER_DIR.glob("dataset_maestro_*.csv"))
    if not files:
        raise FileNotFoundError("No hay dataset maestro")
    return files[-1]


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["precio_original"] = pd.to_numeric(frame["precio_original"], errors="coerce")
    frame["habitaciones"] = pd.to_numeric(frame["habitaciones"], errors="coerce")
    frame["banos"] = pd.to_numeric(frame["banos"], errors="coerce")
    frame["superficie_m2"] = pd.to_numeric(frame["superficie_m2"], errors="coerce") if "superficie_m2" in frame else np.nan
    frame["canal_normalizado"] = frame["canal"].fillna("desconocido").astype(str).str.lower()

    def canal(row):
        if row["fuente"] == "HogarEnCuba":
            return "HogarEnCuba (fichas estructuradas)"
        if row["fuente"] == "Cubisima":
            return "Cubisima (plataforma estructurada)"
        return "Revolico (clasificado informal)"

    frame["canal_grafico"] = frame.apply(canal, axis=1)
    return frame


def summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source, g in frame.groupby("fuente"):
        rows.append({
            "fuente": source,
            "anuncios": len(g),
            "ubicacion_pct": round(100 * g["ubicacion_raw"].notna().mean(), 1),
            "habitaciones_pct": round(100 * g["habitaciones"].notna().mean(), 1),
            "banos_pct": round(100 * g["banos"].notna().mean(), 1),
            "m2_pct": round(100 * g["superficie_m2"].notna().mean(), 1),
            "precio_pct": round(100 * g["precio_original"].notna().mean(), 1),
            "moneda_pct": round(100 * g["moneda"].notna().mean(), 1),
            "fecha_pct": round(100 * g["fecha_publicacion"].notna().mean(), 1),
        })
    return pd.DataFrame(rows)


def channel_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for canal, g in frame.groupby("canal_grafico"):
        rows.append({
            "canal": canal,
            "anuncios": len(g),
            "anuncios_con_precio": int(g["precio_original"].notna().sum()),
            "mediana_precio": g["precio_original"].median(),
            "con_banos_pct": round(100 * g["banos"].notna().mean(), 1),
            "con_m2_pct": round(100 * g["superficie_m2"].notna().mean(), 1),
            "con_fecha_pct": round(100 * g["fecha_publicacion"].notna().mean(), 1),
        })
    return pd.DataFrame(rows)


def plot_coverage(summary: pd.DataFrame):
    metrics = ["ubicacion_pct", "habitaciones_pct", "banos_pct", "m2_pct", "precio_pct", "moneda_pct", "fecha_pct"]
    long = summary.melt(id_vars="fuente", value_vars=metrics, var_name="variable", value_name="cobertura_pct")
    long["variable"] = long["variable"].str.replace("_pct", "", regex=False)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    sns.barplot(data=long, x="variable", y="cobertura_pct", hue="fuente", ax=ax)
    ax.set_ylabel("Cobertura (%)")
    ax.set_title("Cobertura de metadatos por fuente")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=25, ha="right")
    plt.tight_layout()
    fig.savefig(OUT / "01_cobertura_por_fuente.png", dpi=140, facecolor="white")
    plt.close(fig)


def plot_channel_price(frame: pd.DataFrame):
    valid = frame[frame["precio_original"].notna()].copy()
    valid = valid[~valid["precio_sospechoso"].fillna(False).astype(bool)] if "precio_sospechoso" in valid else valid
    if valid.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(data=valid, x="canal_grafico", y="precio_original", hue="fuente", ax=ax, showfliers=False)
    ax.set_title("Precio original por canal")
    ax.set_ylabel("Precio (moneda original)")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=12, ha="right")
    plt.tight_layout()
    fig.savefig(OUT / "02_precio_por_canal.png", dpi=140, facecolor="white")
    plt.close(fig)


def plot_channel_m2(channel: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(channel["canal"], channel["con_m2_pct"], color=["#4472c4", "#70ad47", "#ffc759"][:len(channel)])
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in channel["con_m2_pct"]], padding=2)
    ax.set_title("Cobertura de superficie (m²) por canal")
    ax.set_ylabel("% de anuncios con m²")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=12, ha="right")
    plt.tight_layout()
    fig.savefig(OUT / "03_cobertura_m2_por_canal.png", dpi=140, facecolor="white")
    plt.close(fig)


def plot_currency_percentage(frame: pd.DataFrame):
    counts = frame.groupby(["fuente", "moneda"]).size().unstack(fill_value=0)
    pct = counts.div(counts.sum(axis=1), axis=0) * 100
    pct = pct.fillna(0)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    pct.plot(kind="bar", stacked=True, ax=ax, colormap="viridis")
    ax.set_title("Composición de moneda por fuente (%)")
    ax.set_ylabel("Porcentaje")
    plt.tight_layout()
    fig.savefig(OUT / "04_moneda_por_fuente.png", dpi=140, facecolor="white")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(newest_master(), dtype=str)
    frame = prepare(frame)
    sources = summary_table(frame)
    channels = channel_summary(frame)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sources.to_csv(OUT / f"cobertura_por_fuente_{stamp}.csv", index=False, encoding="utf-8-sig")
    channels.to_csv(OUT / f"comparativo_canales_{stamp}.csv", index=False, encoding="utf-8-sig")

    plot_coverage(sources)
    plot_channel_price(frame)
    plot_channel_m2(channels)
    plot_currency_percentage(frame)

    # print top-line answers
    print("COBERTURA POR FUENTE")
    print(sources.to_string(index=False))
    print("")
    print("COMPARATIVO POR CANAL")
    print(channels.to_string(index=False))

    md = OUT / f"comparativo_fuentes_{stamp}.md"
    md.write_text(
        "## Cobertura por fuente\n\n" + sources.to_markdown(index=False) + "\n\n" +
        "## Comparativo por canal\n\n" + channels.to_markdown(index=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nResumen guardado en: {md}")


if __name__ == "__main__":
    main()