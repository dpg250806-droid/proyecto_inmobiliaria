#!/usr/bin/env python3
"""Segmenta viviendas por terciles de precio y perfiles de habitaciones."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns

from precio_moneda import detalle_analisis, normalizar_moneda, precios_analisis

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
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    # El precio de analisis prefiere la reextraccion manual y excluye los campos
    # sospechosos; `precio_original` queda disponible para auditoria.
    frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    # Habitaciones y banos de analisis (texto del anuncio, campo publicado o slug);
    # `detalle_analisis` cae al campo publicado si no hay columnas de reextraccion.
    # La superficie (m2) queda fuera: ninguna fuente la publica al 100%.
    (
        frame["habitaciones"],
        frame["banos"],
        _,
        _,
    ) = detalle_analisis(frame)
    frame = frame[
        frame["precio_analisis"].notna()
        & frame["habitaciones"].notna()
        & frame["moneda_analisis"].ne("")
    ].copy()
    if frame.empty:
        return frame

    def price_groups(prices):
        corte_inferior = prices.quantile(0.33)
        corte_superior = prices.quantile(0.66)
        return prices.map(
            lambda value: "economica"
            if value <= corte_inferior
            else "media"
            if value <= corte_superior
            else "alta"
        )

    def room_profile(value):
        if value <= 2:
            return "pequena (<=2)"
        if value <= 4:
            return "mediana (3-4)"
        return "amplia (5+)"

    frame["grupo_precio"] = frame.groupby("moneda_analisis", group_keys=False)["precio_analisis"].apply(price_groups)
    frame["perfil_habitaciones"] = frame["habitaciones"].apply(room_profile)
    frame["con_banos"] = frame["banos"].notna()
    return frame


def summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.groupby(["moneda_analisis", "grupo_precio", "perfil_habitaciones"]).agg(
        anuncios=("precio_analisis", "count"),
        precio_mediano=("precio_analisis", "median"),
        habitaciones_mediana=("habitaciones", "median"),
        banos_mediana=("banos", "median"),
    ).reset_index()
    return table


def plot_segment(frame: pd.DataFrame, out: Path):
    counts = frame.groupby("moneda_analisis").size()
    usables = counts[counts >= 5].index
    excluidas = counts[counts < 5]
    plot = frame[frame["moneda_analisis"].isin(usables)].copy()
    if plot.empty:
        return
    plot["grupo_etiqueta"] = plot["grupo_precio"].map(
        {"economica": "Económica", "media": "Media", "alta": "Alta"}
    )
    graph = sns.relplot(
        data=plot,
        x="habitaciones",
        y="precio_analisis",
        hue="grupo_etiqueta",
        hue_order=["Económica", "Media", "Alta"],
        col="moneda_analisis",
        col_wrap=2,
        kind="scatter",
        alpha=0.55,
        height=4,
        aspect=1.2,
        palette={"Económica": "#9bb7d4", "Media": "#4472c4", "Alta": "#1f3864"},
    )
    graph.set(yscale="log")
    graph.set_axis_labels("Habitaciones", "Precio de análisis (escala log)")
    graph.set_titles("Moneda: {col_name}")
    try:
        graph.legend.set_title("Grupo de precio")
    except AttributeError:
        pass
    detalle = "; ".join(f"{moneda}: {n}" for moneda, n in counts[usables].items())
    nota = ""
    if not excluidas.empty:
        nota = " | sin gráfico por n<5: " + ", ".join(f"{m}: {n}" for m, n in excluidas.items())
    graph.fig.suptitle(
        f"Perfil por precio y habitaciones (precios separados por moneda; n: {detalle}){nota}",
        y=1.02,
    )
    graph.fig.savefig(
        out / "segmentos_precio_habitaciones.png", dpi=140, facecolor="white", bbox_inches="tight"
    )
    plt.close(graph.fig)


def plot_source_segment(frame: pd.DataFrame, out: Path):
    counts = frame.groupby("moneda_analisis").size()
    usables = counts[counts >= 5].index
    excluidas = counts[counts < 5]
    plot = frame[frame["moneda_analisis"].isin(usables)].copy()
    if plot.empty:
        return
    currencies = sorted(plot["moneda_analisis"].dropna().unique())
    fig, axes = plt.subplots(1, len(currencies), figsize=(7 * len(currencies), 5.2), squeeze=False)
    colores = {"economica": "#9bb7d4", "media": "#4472c4", "alta": "#1f3864"}
    etiquetas = {"economica": "Económica", "media": "Media", "alta": "Alta"}
    leyenda = None
    for ax, currency in zip(axes[0], currencies):
        table = (
            plot.loc[plot["moneda_analisis"].eq(currency)]
            .groupby(["fuente", "grupo_precio"])
            .size()
            .unstack(fill_value=0)
        )
        orden = [grupo for grupo in ["economica", "media", "alta"] if grupo in table.columns]
        table = table.reindex(columns=orden, fill_value=0)
        counts_pct = table.div(table.sum(axis=1), axis=0).fillna(0) * 100
        counts_pct.rename(columns=etiquetas).plot(
            kind="bar",
            stacked=True,
            ax=ax,
            color=[colores[grupo] for grupo in orden],
            width=0.7,
            legend=False,
        )
        ax.set_title(f"Moneda: {currency} (n={int(table.values.sum())})")
        ax.set_ylabel("Porcentaje de anuncios")
        ax.set_xlabel("Fuente")
        ax.set_ylim(0, 100)
        etiquetas_x = [
            f"{fuente}\n(n={int(table.loc[fuente].sum())})" for fuente in table.index
        ]
        ax.set_xticklabels(etiquetas_x, rotation=15, ha="right")
        if leyenda is None:
            leyenda = (
                [Patch(facecolor=colores[grupo]) for grupo in orden],
                [etiquetas[grupo] for grupo in orden],
            )
    nota = ""
    if not excluidas.empty:
        nota = "Sin gráfico por n<5: " + ", ".join(f"{m}: {n}" for m, n in excluidas.items())
    fig.suptitle("Grupos de precio por fuente, separados por moneda", y=1.01)
    if leyenda is not None:
        fig.legend(
            leyenda[0],
            leyenda[1],
            title="Grupo de precio",
            loc="lower center",
            bbox_to_anchor=(0.5, -0.06),
            ncol=3,
            frameon=False,
        )
    if nota:
        fig.text(0.5, -0.1, nota, ha="center", va="top", fontsize=8)
    fig.tight_layout()
    fig.savefig(
        out / "segmentos_precio_por_fuente.png", dpi=140, facecolor="white", bbox_inches="tight"
    )
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