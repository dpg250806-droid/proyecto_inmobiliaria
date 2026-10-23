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

from precio_moneda import detalle_analisis, normalizar_moneda, precios_analisis
from salidas import nueva_ruta_salida

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
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    if "precio_sospechoso" in frame:
        frame["precio_sospechoso"] = frame["precio_sospechoso"].astype(str).str.strip().str.lower().isin(["true", "1", "yes", "si", "sí"])
    # El precio de analisis prefiere la reextraccion manual y excluye los campos
    # sospechosos; la cobertura (summary_table) sigue midiendo el campo publicado.
    frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    # Habitaciones y banos de analisis (texto del anuncio, campo publicado o slug);
    # `detalle_analisis` cae al campo publicado si no hay columnas de reextraccion.
    # Se usan para las metricas de canal; la cobertura por fuente sigue midiendo
    # el campo publicado. La superficie (m2) queda fuera del analisis porque
    # ninguna fuente la publica de forma sistemática.
    (
        frame["habitaciones_analisis"],
        frame["banos_analisis"],
        _,
        _,
    ) = detalle_analisis(frame)
    frame["canal_normalizado"] = frame["canal"].fillna("desconocido").astype(str).str.lower()

    def canal(row):
        if row["fuente"] == "HogarEnCuba":
            return "HogarEnCuba (fichas estructuradas)"
        if row["fuente"] == "Cubisima":
            return "Cubisima (plataforma estructurada)"
        return "Revolico (clasificado informal)"

    frame["canal_grafico"] = frame.apply(canal, axis=1)
    # Columnas derivadas que pueden faltar en maestros antiguos o en pruebas.
    if "municipio_homologado" not in frame:
        frame["municipio_homologado"] = ""
    if "fecha_reextraida" not in frame:
        frame["fecha_reextraida"] = ""
    return frame


def summary_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Cobertura del campo publicado (no mide la cobertura del analisis)."""
    rows = []
    for source, g in frame.groupby("fuente"):
        rows.append({
            "fuente": source,
            "anuncios": len(g),
            "ubicacion_pct": round(100 * g["ubicacion_raw"].notna().mean(), 1),
            "habitaciones_pct": round(100 * g["habitaciones"].notna().mean(), 1),
            "banos_pct": round(100 * g["banos"].notna().mean(), 1),
            "precio_pct": round(100 * g["precio_original"].notna().mean(), 1),
            "moneda_pct": round(100 * g["moneda"].ne("").mean(), 1),
            "fecha_pct": round(100 * g["fecha_publicacion"].notna().mean(), 1),
        })
    return pd.DataFrame(rows)


def analysis_coverage_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Cobertura del mejor dato disponible para el analisis.

    Separa lo que la fuente publica en un campo (summary_table) de lo que se
    recupera del texto, la pagina o el slug. Es la tabla que debe citarse al
    describir habitaciones, banos, municipio o fecha del analisis.
    """
    rows = []
    for source, g in frame.groupby("fuente"):
        fecha_publicada = g["fecha_publicacion"].fillna("").astype(str).str.strip().ne("")
        fecha_analisis = fecha_publicada | g["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
        rows.append({
            "fuente": source,
            "anuncios": len(g),
            "precio_analisis_pct": round(100 * g["precio_analisis"].notna().mean(), 1),
            "ubicacion_analisis_pct": round(100 * g["ubicacion_analisis"].fillna("").astype(str).str.strip().ne("").mean(), 1),
            "municipio_homologado_pct": round(100 * g["municipio_homologado"].fillna("").astype(str).str.strip().ne("").mean(), 1),
            "habitaciones_analisis_pct": round(100 * g["habitaciones_analisis"].notna().mean(), 1),
            "banos_analisis_pct": round(100 * g["banos_analisis"].notna().mean(), 1),
            "fecha_analisis_pct": round(100 * fecha_analisis.mean(), 1),
        })
    return pd.DataFrame(rows)


def channel_summary(frame: pd.DataFrame, min_currency: int = 5, min_pair: int = 10) -> pd.DataFrame:
    rows = []
    usable = frame[
        frame["precio_analisis"].notna()
        & frame["moneda_analisis"].ne("")
    ]
    currency_counts = usable.groupby("moneda_analisis").size()
    currencies = currency_counts[currency_counts >= min_currency].index
    usable = usable[usable["moneda_analisis"].isin(currencies)]
    pair_counts = usable.groupby(["moneda_analisis", "canal_grafico"]).size()
    pairs = pair_counts[pair_counts >= min_pair].index
    usable = usable[
        usable.set_index(["moneda_analisis", "canal_grafico"]).index.isin(pairs)
    ]
    for (canal, currency), g in usable.groupby(["canal_grafico", "moneda_analisis"]):
        fecha_publicada = g["fecha_publicacion"].fillna("").astype(str).str.strip().ne("")
        fecha_analisis = fecha_publicada | g["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
        rows.append({
            "canal": canal,
            "moneda": currency,
            "anuncios": len(g),
            "anuncios_con_precio": int(g["precio_analisis"].notna().sum()),
            "mediana_precio": g["precio_analisis"].median(),
            "con_habitaciones_pct": round(100 * g["habitaciones_analisis"].notna().mean(), 1),
            "con_banos_pct": round(100 * g["banos_analisis"].notna().mean(), 1),
            "con_fecha_publicada_pct": round(100 * fecha_publicada.mean(), 1),
            "con_fecha_analisis_pct": round(100 * fecha_analisis.mean(), 1),
        })
    return pd.DataFrame(rows)


def plot_coverage(summary: pd.DataFrame, stamp: str | None = None):
    metrics = ["ubicacion_pct", "habitaciones_pct", "banos_pct", "precio_pct", "moneda_pct", "fecha_pct"]
    long = summary.melt(id_vars="fuente", value_vars=metrics, var_name="variable", value_name="cobertura_pct")
    long["variable"] = long["variable"].str.replace("_pct", "", regex=False)
    etiquetas = {
        "ubicacion": "Ubicación",
        "habitaciones": "Habitaciones",
        "banos": "Baños",
        "precio": "Precio",
        "moneda": "Moneda",
        "fecha": "Fecha",
    }
    long["variable"] = long["variable"].map(etiquetas).fillna(long["variable"])
    fig, ax = plt.subplots(figsize=(11, 5.5))
    sns.barplot(data=long, x="variable", y="cobertura_pct", hue="fuente", ax=ax)
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Campo publicado")
    ax.set_title("Cobertura del campo publicado por fuente")
    ax.set_ylim(0, 100)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    ax.legend(title="Fuente", loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(nueva_ruta_salida(OUT, "01_cobertura_por_fuente.png", stamp), dpi=140, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def plot_analysis_coverage(coverage: pd.DataFrame, stamp: str | None = None):
    metrics = [
        "precio_analisis_pct",
        "ubicacion_analisis_pct",
        "municipio_homologado_pct",
        "habitaciones_analisis_pct",
        "banos_analisis_pct",
        "fecha_analisis_pct",
    ]
    long = coverage.melt(id_vars="fuente", value_vars=metrics, var_name="variable", value_name="cobertura_pct")
    long["variable"] = long["variable"].str.replace("_pct", "", regex=False)
    etiquetas = {
        "precio_analisis": "Precio",
        "ubicacion_analisis": "Ubicación",
        "municipio_homologado": "Municipio",
        "habitaciones_analisis": "Habitaciones",
        "banos_analisis": "Baños",
        "fecha_analisis": "Fecha",
    }
    long["variable"] = long["variable"].map(etiquetas).fillna(long["variable"])
    fig, ax = plt.subplots(figsize=(11, 5.5))
    sns.barplot(data=long, x="variable", y="cobertura_pct", hue="fuente", ax=ax)
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Dato")
    ax.set_title("Cobertura del dato de análisis por fuente (texto, página o slug)")
    ax.set_ylim(0, 100)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    ax.legend(title="Fuente", loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(nueva_ruta_salida(OUT, "01b_cobertura_analisis_por_fuente.png", stamp), dpi=140, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def plot_channel_price(frame: pd.DataFrame, stamp: str | None = None):
    valid = frame[frame["precio_analisis"].notna() & frame["moneda_analisis"].ne("")].copy()
    if valid.empty:
        return
    counts = valid.groupby("moneda_analisis").size()
    usables = counts[counts >= 5].index
    excluidas = counts[counts < 5]
    valid = valid[valid["moneda_analisis"].isin(usables)].copy()
    pares = valid.groupby(["moneda_analisis", "canal_grafico"]).size()
    excluidas_pares = pares[pares < 10]
    valid = valid[
        valid.set_index(["moneda_analisis", "canal_grafico"]).index.isin(pares[pares >= 10].index)
    ]
    if valid.empty:
        return
    monedas = [m for m in ["CUC", "USD", "EUR", "CUP"] if m in set(valid["moneda_analisis"])]
    fig, axes = plt.subplots(1, len(monedas), figsize=(6.4 * len(monedas), 5.2), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, moneda in zip(axes, monedas):
        data = valid[valid["moneda_analisis"].eq(moneda)].copy()
        orden = list(data["canal_grafico"].drop_duplicates())
        sns.boxplot(
            data=data,
            x="canal_grafico",
            y="precio_analisis",
            order=orden,
            ax=ax,
            color="#4472c4",
            showfliers=False,
            width=0.6,
        )
        ax.set_yscale("log")
        ax.set_title(f"Moneda: {moneda}")
        ax.set_xlabel("Canal")
        ax.set_ylabel("Precio de análisis (escala log)" if moneda == monedas[0] else "")
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    notas = []
    if not excluidas.empty:
        notas.append("moneda n<5: " + ", ".join(f"{m}: {n}" for m, n in excluidas.items()))
    if not excluidas_pares.empty:
        notas.append(
            "canal-moneda n<10: "
            + ", ".join(f"{c}/{m}: {n}" for (m, c), n in excluidas_pares.items())
        )
    fig.suptitle("Precio de análisis por canal, separado por moneda", y=1.02)
    if notas:
        fig.text(0.5, -0.02, "Sin gráfico: " + " | ".join(notas), ha="center", va="top", fontsize=8)
    fig.tight_layout()
    fig.savefig(nueva_ruta_salida(OUT, "02_precio_por_canal.png", stamp), dpi=140, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def plot_channel_rooms(frame: pd.DataFrame, stamp: str | None = None):
    channel = frame.groupby("canal_grafico").agg(
        con_habitaciones_pct=("habitaciones_analisis", lambda s: round(100 * s.notna().mean(), 1))
    ).reset_index()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(
        channel["canal_grafico"],
        channel["con_habitaciones_pct"],
        color=["#4472c4", "#70ad47", "#ffc759"][:len(channel)],
    )
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in channel["con_habitaciones_pct"]], padding=2)
    ax.set_title("Cobertura de habitaciones (mejor dato disponible) por canal")
    ax.set_ylabel("% de anuncios con habitaciones")
    ax.set_ylim(0, 108)
    plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
    plt.tight_layout()
    fig.savefig(nueva_ruta_salida(OUT, "03_cobertura_habitaciones_por_canal.png", stamp), dpi=140, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def plot_currency_percentage(frame: pd.DataFrame, stamp: str | None = None):
    work = frame.copy()
    work["moneda"] = work["moneda"].replace("", "sin dato")
    counts = work.groupby(["fuente", "moneda"]).size().unstack(fill_value=0)
    pct = counts.div(counts.sum(axis=1), axis=0) * 100
    pct = pct.fillna(0)
    fig, ax = plt.subplots(figsize=(8, 5))
    pct.plot(kind="bar", stacked=True, ax=ax, colormap="viridis")
    ax.set_title("Composición de moneda publicada por fuente (%)")
    ax.set_ylabel("Porcentaje")
    ax.set_xlabel("Fuente")
    ax.set_ylim(0, 100)
    plt.setp(ax.get_xticklabels(), rotation=0)
    ax.legend(title="Moneda", loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=5, frameon=False)
    fig.tight_layout()
    fig.savefig(nueva_ruta_salida(OUT, "04_moneda_por_fuente.png", stamp), dpi=140, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(newest_master(), dtype=str)
    frame = prepare(frame)
    sources = summary_table(frame)
    coverage = analysis_coverage_table(frame)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    channels = channel_summary(frame)
    sources.to_csv(
        nueva_ruta_salida(OUT, "cobertura_por_fuente.csv", stamp),
        index=False,
        encoding="utf-8-sig",
    )
    coverage.to_csv(
        nueva_ruta_salida(OUT, "cobertura_analisis_por_fuente.csv", stamp),
        index=False,
        encoding="utf-8-sig",
    )
    channels.to_csv(
        nueva_ruta_salida(OUT, "comparativo_canales.csv", stamp),
        index=False,
        encoding="utf-8-sig",
    )

    plot_coverage(sources, stamp)
    plot_analysis_coverage(coverage, stamp)
    plot_channel_price(frame, stamp)
    plot_channel_rooms(frame, stamp)
    plot_currency_percentage(frame, stamp)

    # print top-line answers
    print("COBERTURA DEL CAMPO PUBLICADO POR FUENTE")
    print(sources.to_string(index=False))
    print("")
    print("COBERTURA DEL DATO DE ANALISIS POR FUENTE")
    print(coverage.to_string(index=False))
    print("")
    print("COMPARATIVO POR CANAL")
    print(channels.to_string(index=False))

    md = nueva_ruta_salida(OUT, "comparativo_fuentes.md", stamp)
    md.write_text(
        "## Cobertura del campo publicado por fuente\n\n"
        "Mide el campo tal como aparece en la fuente. No mide la cobertura del análisis: "
        "por ejemplo, Revolico publica pocas habitaciones en el campo, pero el texto del anuncio "
        "eleva la cobertura de análisis.\n\n"
        + sources.to_markdown(index=False)
        + "\n\n## Cobertura del dato de análisis por fuente\n\n"
        "Mejor dato disponible después de leer texto, página y slug. `municipio_homologado_pct` "
        "solo cuenta los 15 municipios de La Habana; las zonas o barrios de Cubisima quedan fuera "
        "de esa columna y se conservan en `ubicacion_analisis_pct`.\n\n"
        + coverage.to_markdown(index=False)
        + "\n\n## Comparativo por canal\n\n"
        "La tabla y el gráfico de precios excluyen monedas con n<5 y pares canal-moneda con n<10; "
        "los pares omitidos se anotan en el gráfico. Los demás resúmenes miden cobertura, no comparan "
        "importes. `con_fecha_publicada_pct` mide el campo publicado; `con_fecha_analisis_pct` suma "
        "la fecha recuperada de la página de Revolico. Son coberturas distintas.\n\n"
        + channels.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"\nResumen guardado en: {md}")


if __name__ == "__main__":
    main()