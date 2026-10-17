#!/usr/bin/env python3
"""Clustering simple por k-medias sobre precio, habitaciones y banos."""
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
OUT = ROOT / "outputs" / "clustering"


def newest(directory, pattern):
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(directory / pattern)
    return files[-1]


def kmeans(data, k=3, iterations=100, seed=42):
    rng = np.random.default_rng(seed)
    centroids = data[rng.choice(len(data), size=k, replace=False)]
    labels = np.zeros(len(data), dtype=int)
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
    # Cubisima es la fuente con mejor cobertura de precio/habitaciones/banos.
    data = frame[(frame["fuente"] == "Cubisima") & frame["precio_original"].notna() & frame["habitaciones"].notna() & frame["banos"].notna()].copy()
    if len(data) < 30:
        print("No hay suficientes datos completos para clustering.")
        return

    x = data[["precio_original", "habitaciones", "banos"]].to_numpy(dtype=float)
    x_std = (x - x.mean(axis=0)) / x.std(axis=0)
    labels, centers_std = kmeans(x_std, k=3)
    data["cluster"] = labels
    centers = centers_std * x.std(axis=0) + x.mean(axis=0)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data.to_csv(OUT / f"clusters_cubisima_{stamp}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(centers, columns=["precio_medio", "habitaciones_media", "banos_media"]).to_csv(
        OUT / f"centroides_clusters_{stamp}.csv", index=False, encoding="utf-8-sig"
    )

    profile = data.groupby("cluster").agg(
        anuncios=("precio_original", "count"),
        precio_mediano=("precio_original", "median"),
        habitaciones_mediana=("habitaciones", "median"),
        banos_mediana=("banos", "median"),
    ).reset_index()
    print(profile.to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.scatterplot(data=data, x="habitaciones", y="precio_original", hue="cluster", palette="deep", ax=ax)
    ax.set_title("Clustering de Cubisima por precio, habitaciones y banos")
    ax.set_xlabel("Habitaciones")
    ax.set_ylabel("Precio original (EUR)")
    plt.tight_layout()
    fig.savefig(OUT / "clusters_cubisima.png", dpi=140, facecolor="white")
    plt.close(fig)
    print(f"Clusters guardados en {OUT}")


if __name__ == "__main__":
    main()