#!/usr/bin/env python3
"""Clustering por k-medias sobre precio, habitaciones y banos."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from precio_moneda import normalizar_moneda

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
    frame["habitaciones"] = pd.to_numeric(frame["habitaciones"], errors="coerce")
    frame["banos"] = pd.to_numeric(frame["banos"], errors="coerce")
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    if "precio_sospechoso" in frame:
        suspicious = frame["precio_sospechoso"].astype(str).str.strip().str.lower().isin(["true", "1", "yes", "si", "sí"])
    else:
        suspicious = pd.Series(False, index=frame.index)
    data = frame[
        (frame["fuente"] == "Cubisima")
        & frame["precio_original"].notna()
        & frame["habitaciones"].notna()
        & frame["banos"].notna()
        & frame["moneda"].ne("")
        & ~suspicious
    ].copy()
    usable_currencies = data["moneda"].value_counts()
    usable_currencies = usable_currencies[usable_currencies >= 30].index
    data = data[data["moneda"].isin(usable_currencies)].copy()
    if data.empty:
        print("No hay suficientes datos completos para clustering.")
        return

    data["cluster"] = -1
    center_rows = []
    for currency, currency_rows in data.groupby("moneda"):
        x = currency_rows[["precio_original", "habitaciones", "banos"]].to_numpy(dtype=float)
        means = x.mean(axis=0)
        scales = x.std(axis=0)
        scales[scales == 0] = 1
        x_std = (x - means) / scales
        labels, centers_std = kmeans(x_std, k=3)
        data.loc[currency_rows.index, "cluster"] = labels
        centers = centers_std * scales + means
        for label, center in enumerate(centers):
            center_rows.append({
                "moneda": currency,
                "cluster": label,
                "precio_medio": center[0],
                "habitaciones_media": center[1],
                "banos_media": center[2],
            })

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data.to_csv(OUT / f"clusters_cubisima_{stamp}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(center_rows).to_csv(OUT / f"centroides_clusters_{stamp}.csv", index=False, encoding="utf-8-sig")

    profile = data.groupby(["moneda", "cluster"]).agg(
        anuncios=("precio_original", "count"),
        precio_mediano=("precio_original", "median"),
        habitaciones_mediana=("habitaciones", "median"),
        banos_mediana=("banos", "median"),
    ).reset_index()
    print(profile.to_string(index=False))

    graph = sns.relplot(
        data=data,
        x="habitaciones",
        y="precio_original",
        hue="cluster",
        col="moneda",
        col_wrap=2,
        kind="scatter",
        palette="deep",
    )
    graph.set_axis_labels("Habitaciones", "Precio original")
    graph.set_titles("Moneda: {col_name}")
    graph.fig.suptitle("Clustering de Cubisima (precios separados por moneda)", y=1.02)
    graph.fig.savefig(OUT / "clusters_cubisima.png", dpi=140, facecolor="white")
    plt.close(graph.fig)
    print(f"Clusters guardados en {OUT}")


if __name__ == "__main__":
    main()