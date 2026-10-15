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
    frame = frame[frame["precio_original"].notna() & frame["habitaciones"].notna()].copy()
    if frame.empty:
        return frame

    def price_group(value):
        if pd.isna(value):
            return "sin precio"
        # Usar percentiles globales para un primer perfil.
        q1 = frame["precio_original"].quantile(0.33)
        q2 = frame["precio_original"].quantile(0.66)
        if value <= q1:
            return "economica"
        if value <= q2:
            return "media"
        return "alta"

    def room_profile(value):
        if value <= 2:
            return "pequena (<=2)"
        if value <= 4:
            return "mediana (3-4)"
        return "amplia (5+)"

    frame["grupo_precio"] = frame["precio_original"].apply(price_group)
    frame["perfil_habitaciones"] = frame["habitaciones"].apply(room_profile)
    frame["con_banos"] = frame["banos"].notna()
    frame["con_m2"] = frame["superficie_m2"].notna()
    return frame


def summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.groupby(["grupo_precio", "perfil_habitaciones"]).agg(
        anuncios=("precio_original", "count"),
        precio_mediano=("precio_original", "median"),
        habitaciones_mediana=("habitaciones", "median"),
        banos_mediana=("banos", "median"),
        con_m2=("con_m2", "sum"),
    ).reset_index()
    return table


def plot_segment(frame: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(9, 5))
    palette = {"economica": "#9bb7d4", "media": "#4472c4", "alta": "#1f3864"}
    for grupo, g in frame.groupby("grupo_precio"):
        ax.scatter(g["habitaciones"], g["precio_original"], label=grupo, alpha=0.55, s=45, color=palette.get(grupo))
    ax.set_xlabel("Habitaciones")
    ax.set_ylabel("Precio original (moneda nativa)")
    ax.set_title("Perfil de viviendas por precio y habitaciones")
    ax.legend(title="grupo por precio")
    plt.tight_layout()
    fig.savefig(out / "segmentos_precio_habitaciones.png", dpi=140, facecolor="white")
    plt.close(fig)


def plot_source_segment(frame: pd.DataFrame, out: Path):
    table = frame.groupby(["fuente", "grupo_precio"]).size().unstack(fill_value=0)
    counts = table.div(table.sum(axis=1), axis=0) * 100
    counts = counts.fillna(0)
    fig, ax = plt.subplots(figsize=(9, 5))
    counts.plot(kind="bar", stacked=True, ax=ax, colormap="Blues")
    ax.set_title("Composicion de grupos de precio por fuente (%)")
    ax.set_ylabel("Porcentaje")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=15, ha="right")
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