#!/usr/bin/env python3
"""Segmenta viviendas por cuartiles de precio y perfiles de habitaciones."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from precio_moneda import normalizar_moneda, precios_analisis

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "outputs" / "segmentacion"

sns.set_theme(style="whitegrid")


def newest(dataset_dir: Path) -> Path:
    files = sorted(dataset_dir.glob("dataset_maestro_*.csv"))
    if not files:
        raise FileNotFoundError(dataset_dir)
    return files[-1]


def build_segments(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["precio_original"] = pd.to_numeric(frame["precio_original"], errors="coerce")
    frame["habitaciones"] = pd.to_numeric(frame["habitaciones"], errors="coerce")
    frame["banos"] = pd.to_numeric(frame["banos"], errors="coerce")
    frame["superficie_m2"] = pd.to_numeric(frame["superficie_m2"], errors="coerce") if "superficie_m2" in frame else pd.NA
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    # El precio de analisis prefiere la reextraccion manual y excluye los campos
    # sospechosos; `precio_original` queda disponible para auditoria.
    frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    frame = frame[
        frame["precio_analisis"].notna()
        & frame["habitaciones"].notna()
        & frame["moneda_analisis"].ne("")
    ].copy()
    if frame.empty:
        return frame

    def price_groups(prices):
        q1 = prices.quantile(0.33)
        q2 = prices.quantile(0.66)
        return prices.map(lambda value: "economica" if value <= q1 else "media" if value <= q2 else "alta")

    def room_profile(value):
        if value <= 2:
            return "pequena (<=2)"
        if value <= 4:
            return "mediana (3-4)"
        return "amplia (5+)"

    frame["grupo_precio"] = frame.groupby("moneda_analisis", group_keys=False)["precio_analisis"].apply(price_groups)
    frame["perfil_habitaciones"] = frame["habitaciones"].apply(room_profile)
    frame["con_banos"] = frame["banos"].notna()
    frame["con_m2"] = frame["superficie_m2"].notna()
    return frame


def summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.groupby(["moneda_analisis", "grupo_precio", "perfil_habitaciones"]).agg(
        anuncios=("precio_analisis", "count"),
        precio_mediano=("precio_analisis", "median"),
        habitaciones_mediana=("habitaciones", "median"),
        banos_mediana=("banos", "median"),
        con_m2=("con_m2", "sum"),
    ).reset_index()
    return table


def plot_segment(frame: pd.DataFrame, out: Path):
    graph = sns.relplot(
        data=frame,
        x="habitaciones",
        y="precio_analisis",
        hue="grupo_precio",
        col="moneda_analisis",
        col_wrap=2,
        kind="scatter",
        alpha=0.55,
        height=4,
        aspect=1.2,
        palette={"economica": "#9bb7d4", "media": "#4472c4", "alta": "#1f3864"},
    )
    graph.set_axis_labels("Habitaciones", "Precio de analisis")
    graph.set_titles("Moneda: {col_name}")
    graph.fig.suptitle("Perfil por precio y habitaciones (precios separados por moneda)", y=1.02)
    graph.fig.savefig(out / "segmentos_precio_habitaciones.png", dpi=140, facecolor="white")
    plt.close(graph.fig)


def plot_source_segment(frame: pd.DataFrame, out: Path):
    currencies = sorted(frame["moneda_analisis"].dropna().unique())
    fig, axes = plt.subplots(1, len(currencies), figsize=(7 * len(currencies), 5), squeeze=False)
    for ax, currency in zip(axes[0], currencies):
        table = frame.loc[frame["moneda_analisis"].eq(currency)].groupby(["fuente", "grupo_precio"]).size().unstack(fill_value=0)
        counts = table.div(table.sum(axis=1), axis=0).fillna(0) * 100
        counts.plot(kind="bar", stacked=True, ax=ax, colormap="Blues")
        ax.set_title(f"Moneda: {currency}")
        ax.set_ylabel("Porcentaje")
        ax.set_xlabel("Fuente")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=15, ha="right")
    fig.suptitle("Grupos de precio por fuente, separados por moneda")
    plt.tight_layout()
    fig.savefig(out / "segmentos_precio_por_fuente.png", dpi=140, facecolor="white")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(newest(MASTER_DIR), dtype=str)
    seg = build_segments(frame)
    if seg.empty:
        print("No hay datos suficientes para segmentar")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"segmentacion_viviendas_{stamp}.csv"
    seg.to_csv(path, index=False, encoding="utf-8-sig")

    table = summary_table(seg)
    table_path = OUT / f"resumen_segmentacion_{stamp}.csv"
    table.to_csv(table_path, index=False, encoding="utf-8-sig")

    plot_segment(seg, OUT)
    plot_source_segment(seg, OUT)

    print(f"Segmentos guardados en {path}")
    print(f"Resumen: {table_path}")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()