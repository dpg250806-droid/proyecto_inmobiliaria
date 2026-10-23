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
from salidas import nueva_ruta_salida

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "outputs" / "clustering"


def newest(directory, pattern):
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(directory / pattern)
    return files[-1]


def kmeans(data, k=3, iterations=100, seed=42, n_init=10):
    """k-means con reinicios multiple y semilla fija (resultado reproducible).

    Con una sola inicializacion la solucion depende del azar y puede cair en
    un optimo local pobre; se prueban `n_init` inicializaciones y se conserva
    la de menor inercia. Con la misma semilla el resultado es siempre el mismo.
    """
    if len(data) < k:
        raise ValueError("k no puede ser mayor que el número de observaciones.")
    mejor = None
    for intento in range(max(1, n_init)):
        rng = np.random.default_rng(seed + intento)
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
        inercia = float(((data - centroids[labels]) ** 2).sum())
        if mejor is None or inercia < mejor[0]:
            mejor = (inercia, labels, centroids)
    return mejor[1], mejor[2]


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
    stability_rows = []
    for currency, currency_rows in data.groupby("moneda_analisis"):
        x = currency_rows[["precio_analisis", "habitaciones", "banos"]].to_numpy(dtype=float)
        # El precio se transforma en logaritmo: la distribucion de precios de
        # vivienda es multiplicativa y, con el precio en escala lineal, la
        # solucion de k-means depende de la semilla (se comprueba en
        # `estabilidad_clusters_*.csv`). El precio se vuelve a su escala
        # original para reportar centroides y medianas.
        caracteristicas = np.column_stack([np.log(x[:, 0]), x[:, 1], x[:, 2]])
        means = caracteristicas.mean(axis=0)
        scales = caracteristicas.std(axis=0)
        scales[scales == 0] = 1
        x_std = (caracteristicas - means) / scales
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
        centers[:, 0] = np.exp(centers[:, 0])
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

        # Estabilidad: se repite el agrupamiento con varias semillas y se
        # anota el tamaño y la mediana de cada grupo.
        for semilla in [42, 7, 2024, 99, 123]:
            etiquetas, _ = kmeans(x_std, k=3, seed=semilla)
            orden_semilla = (
                pd.DataFrame({"c": etiquetas, "p": x[:, 0]})
                .groupby("c")["p"]
                .median()
                .sort_values()
                .index.tolist()
            )
            mapa_semilla = {viejo: nuevo for nuevo, viejo in enumerate(orden_semilla)}
            etiquetas = np.array([mapa_semilla[e] for e in etiquetas])
            for grupo in range(3):
                seleccion = etiquetas == grupo
                stability_rows.append({
                    "moneda": currency,
                    "semilla": semilla,
                    "grupo": grupo,
                    "etiqueta": ["económico", "medio", "alto"][grupo],
                    "anuncios": int(seleccion.sum()),
                    "precio_mediano": float(np.median(x[seleccion, 0])),
                })

    data["cluster_etiqueta"] = data["cluster"].map({0: "económico", 1: "medio", 2: "alto"})

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data.to_csv(
        nueva_ruta_salida(OUT, "clusters_viviendas.csv", stamp),
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(center_rows).to_csv(
        nueva_ruta_salida(OUT, "centroides_clusters.csv", stamp),
        index=False,
        encoding="utf-8-sig",
    )
    estabilidad = pd.DataFrame(stability_rows)
    estabilidad.to_csv(
        nueva_ruta_salida(OUT, "estabilidad_clusters.csv", stamp),
        index=False,
        encoding="utf-8-sig",
    )
    print("Estabilidad (tamaño y mediana de cada grupo en 5 semillas):")
    print(
        estabilidad.groupby(["moneda", "etiqueta"])
        .agg({"anuncios": ["min", "max"], "precio_mediano": ["min", "max"]})
        .round(0)
        .to_string()
    )

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
        nueva_ruta_salida(OUT, "clusters_viviendas.png", stamp),
        dpi=140,
        facecolor="white",
        bbox_inches="tight",
    )
    plt.close(graph.fig)
    print(f"Clusters guardados en {OUT}")


if __name__ == "__main__":
    main()