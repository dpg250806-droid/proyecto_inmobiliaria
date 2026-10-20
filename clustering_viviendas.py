#!/usr/bin/env python3
"""Clustering por k-medias sobre precio, habitaciones y banos.

Agrupa por separado cada moneda con al menos 30 observaciones; excluye precios
sospechosos y filas incompletas. Participan todas las fuentes que tengan los tres
campos disponibles.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from precio_moneda import detalle_analisis, normalizar_moneda, precios_analisis

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "outputs" / "clustering"


def newest(directory, pattern):
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(directory / pattern)
    return files[-1]


def kmeans(data, k=3, iterations=100, seed=42):
    if len(data) < k:
        raise ValueError("k no puede ser mayor que el número de observaciones.")
    rng = np.random.default_rng(seed)
    centroids = data[rng.choice(len(data), size=k, replace=False)]
    labels = np.full(len(data), -1, dtype=int)
    for _ in range(iterations):
        distances = ((data[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_labels = distances.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            labels = new_labels
            break
        labels = new_labels
        for i in range(k):
            if np.any(labels == i):
                centroids[i] = data[labels == i].mean(axis=0)
    return labels, centroids


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(newest(MASTER_DIR, "dataset_maestro_*.csv"), dtype=str)
    frame["precio_original"] = pd.to_numeric(frame["precio_original"], errors="coerce")
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    # El precio de analisis prefiere la reextraccion manual y excluye los campos
    # sospechosos; `precio_original` queda disponible para auditoria.
    frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    # Habitaciones y banos de analisis (texto del anuncio, campo publicado o slug);
    # `detalle_analisis` cae al campo publicado si no hay columnas de reextraccion.
    (
        frame["habitaciones"],
        frame["banos"],
        _,
        _,
    ) = detalle_analisis(frame)
    data = frame[
        frame["precio_analisis"].notna()
        & frame["habitaciones"].notna()
        & frame["banos"].notna()
        & frame["moneda_analisis"].ne("")
    ].copy()
    counts = data["moneda_analisis"].value_counts()
    usable_currencies = counts[counts >= 30].index
    excluidas = counts[counts < 30]
    if not excluidas.empty:
        print(
            "Monedas excluidas (menos de 30 observaciones): "
            + ", ".join(f"{m}: {n}" for m, n in excluidas.items())
        )
    data = data[data["moneda_analisis"].isin(usable_currencies)].copy()
    if data.empty:
        print("No hay suficientes datos completos para clustering.")
        return

    data["cluster"] = -1
    center_rows = []
    for currency, currency_rows in data.groupby("moneda_analisis"):
        x = currency_rows[["precio_analisis", "habitaciones", "banos"]].to_numpy(dtype=float)
        means = x.mean(axis=0)
        scales = x.std(axis=0)
        scales[scales == 0] = 1
        x_std = (x - means) / scales
        labels, centers_std = kmeans(x_std, k=3)
        # Reordenar los grupos por mediana de precio: 0=economico, 1=medio,
        # 2=alto. Asi el numero del cluster es interpretable y estable entre
        # monedas; el agrupamiento en si no cambia.
        temporal = pd.DataFrame({"cluster_original": labels, "precio": x[:, 0]})
        orden = temporal.groupby("cluster_original")["precio"].median().sort_values().index.tolist()
        mapa = {anterior: nuevo for nuevo, anterior in enumerate(orden)}
        labels = np.array([mapa[etiqueta] for etiqueta in labels], dtype=int)
        data.loc[currency_rows.index, "cluster"] = labels
        centers = centers_std * scales + means
        centers = centers[orden]
        for label, center in enumerate(centers):
            center_rows.append({
                "moneda": currency,
                "cluster": label,
                "etiqueta": ["económico", "medio", "alto"][label],
                "precio_medio": center[0],
                "habitaciones_media": center[1],
                "banos_media": center[2],
            })

    data["cluster_etiqueta"] = data["cluster"].map({0: "económico", 1: "medio", 2: "alto"})

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data.to_csv(OUT / f"clusters_viviendas_{stamp}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(center_rows).to_csv(OUT / f"centroides_clusters_{stamp}.csv", index=False, encoding="utf-8-sig")

    profile = data.groupby(["moneda_analisis", "cluster", "cluster_etiqueta"]).agg(
        anuncios=("precio_analisis", "count"),
        precio_mediano=("precio_analisis", "median"),
        habitaciones_mediana=("habitaciones", "median"),
        banos_mediana=("banos", "median"),
    ).reset_index()
    print(profile.to_string(index=False))

    graph = sns.relplot(
        data=data,
        x="habitaciones",
        y="precio_analisis",
        hue="cluster_etiqueta",
        hue_order=["económico", "medio", "alto"],
        col="moneda_analisis",
        col_wrap=2,
        kind="scatter",
        palette={"económico": "#9bb7d4", "medio": "#4472c4", "alto": "#1f3864"},
    )
    graph.set(yscale="log")
    graph.set_axis_labels("Habitaciones", "Precio de análisis (escala log)")
    graph.set_titles("Moneda: {col_name}")
    try:
        graph.legend.set_title("Grupo")
    except AttributeError:
        pass
    detalle = data.groupby("moneda_analisis").size()
    graph.fig.suptitle(
        "Clustering de viviendas (k-means por moneda; grupos ordenados por mediana de precio; "
        + "; ".join(f"{m}: n={n}" for m, n in detalle.items())
        + ")",
        y=1.02,
    )
    graph.fig.savefig(
        OUT / "clusters_viviendas.png", dpi=140, facecolor="white", bbox_inches="tight"
    )
    plt.close(graph.fig)
    print(f"Clusters guardados en {OUT}")


if __name__ == "__main__":
    main()