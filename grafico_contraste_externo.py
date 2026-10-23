#!/usr/bin/env python3
"""Contraste grafico entre nuestros precios pedidos y la referencia externa.

Barras/puntos: mediana de Revolico en USD por municipio (precios pedidos,
octubre de 2026). Referencia: promedio orientativo de CubanOSS Inmobiliaria
(12/06/2025), una fuente comercial que el proyecto cita como contexto y no
como medicion propia.

Se respetan las reglas del proyecto: solo grupos con n>=5, sin mezclar monedas,
y la advertencia de que se comparan precios pedidos con promedios orientativos.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from precio_moneda import precios_analisis
from salidas import nueva_ruta_salida

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "visualizaciones"

# Promedio orientativo de CubanOSS Inmobiliaria (12/06/2025). Cuando la fuente
# publica una banda se guardan los dos extremos.
REFERENCIAS = {
    "Playa": (45_000, 55_000, "Miramar y Siboney"),
    "Plaza de la Revolución": (40_000, 40_000, "Vedado"),
    "Habana Vieja": (35_000, 35_000, ""),
    "Centro Habana": (12_000, 40_000, ""),
    "Arroyo Naranjo": (10_500, 10_500, ""),
    "La Lisa": (12_000, 40_000, ""),
    "San Miguel del Padrón": (8_000, 8_000, ""),
    "Guanabacoa": (9_000, 9_000, ""),
}
FUENTE = "CubanOSS Inmobiliaria, 12/06/2025"
FECHA_DATOS = "Revolico, octubre de 2026"


def miles(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def main() -> None:
    maestro = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))[-1]
    tabla = pd.read_csv(maestro, dtype=str).fillna("")
    tabla["precio_analisis"], tabla["moneda_analisis"] = precios_analisis(tabla)
    tabla["precio_analisis"] = pd.to_numeric(tabla["precio_analisis"], errors="coerce")

    base = tabla[
        tabla["fuente"].eq("Revolico")
        & tabla["moneda_analisis"].eq("USD")
        & tabla["precio_analisis"].notna()
        & tabla["municipio_homologado"].ne("")
    ]
    resumen = (
        base.groupby("municipio_homologado")["precio_analisis"]
        .agg(n="count", mediana="median")
        .reset_index()
    )

    filas = []
    for municipio, (ref_min, ref_max, nota) in REFERENCIAS.items():
        dato = resumen[resumen["municipio_homologado"].eq(municipio)]
        if dato.empty:
            continue
        n = int(dato.iloc[0]["n"])
        mediana = float(dato.iloc[0]["mediana"])
        if n < 5:
            print(f"  {municipio}: n={n} < 5, se excluye de la figura")
            continue
        punto = (ref_min + ref_max) / 2
        filas.append(
            {
                "municipio": municipio,
                "nota_referencia": nota,
                "n_revolico": n,
                "mediana_revolico": mediana,
                "referencia_min": ref_min,
                "referencia_max": ref_max,
                "referencia_punto": punto,
                "tipo_referencia": "banda" if ref_max > ref_min else "punto",
                "diferencia_abs": mediana - punto,
                "diferencia_pct": (mediana - punto) / punto * 100,
                "fuente_externa": FUENTE,
            }
        )

    datos = pd.DataFrame(filas).sort_values("mediana_revolico", ascending=True)
    if datos.empty:
        raise SystemExit("No hay municipios comparables")

    ruta_csv = nueva_ruta_salida(OUT, "datos_contraste_fuentes_externas.csv")
    datos.round(0).to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    print(f"Escrito {ruta_csv}")

    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["savefig.bbox"] = "tight"
    fig, ax = plt.subplots(figsize=(9.8, 6.6))
    azul = "#1f4e79"
    naranja = "#c55a11"
    gris = "#9a9a9a"

    for posicion, fila in enumerate(datos.itertuples(index=False)):
        # Banda de la referencia externa (si es un rango).
        if fila.referencia_max > fila.referencia_min:
            ax.plot(
                [fila.referencia_min, fila.referencia_max],
                [posicion, posicion],
                color=naranja,
                linewidth=7,
                alpha=0.18,
                solid_capstyle="round",
                zorder=1,
            )
        ax.plot(
            [fila.referencia_punto, fila.mediana_revolico],
            [posicion, posicion],
            color=gris,
            linewidth=1.2,
            zorder=2,
        )
        ax.scatter(
            fila.mediana_revolico,
            posicion,
            s=90,
            color=azul,
            edgecolor="white",
            linewidth=0.8,
            zorder=5,
        )
        ax.scatter(
            fila.referencia_punto,
            posicion,
            s=80,
            marker="D",
            color=naranja,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        banda = fila.referencia_max > fila.referencia_min
        ax.annotate(
            f"{miles(fila.mediana_revolico)}  (n={fila.n_revolico})",
            (fila.mediana_revolico, posicion),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            va="bottom",
            fontsize=8.5,
            color=azul,
            fontweight="bold",
        )
        if banda:
            ax.annotate(
                f"{miles(fila.referencia_min)}–{miles(fila.referencia_max)}",
                (fila.referencia_max, posicion),
                textcoords="offset points",
                xytext=(6, 0),
                ha="left",
                va="center",
                fontsize=7.8,
                color=naranja,
            )
        else:
            ax.annotate(
                miles(fila.referencia_min),
                (fila.referencia_punto, posicion),
                textcoords="offset points",
                xytext=(0, -9),
                ha="center",
                va="top",
                fontsize=8,
                color=naranja,
            )

    etiquetas = [
        f"{fila.municipio}  ({fila.nota_referencia})" if fila.nota_referencia else fila.municipio
        for fila in datos.itertuples(index=False)
    ]
    ax.set_yticks(range(len(datos)))
    ax.set_yticklabels(etiquetas, fontsize=9.5)
    ax.set_ylim(-0.7, len(datos) - 0.3)
    ax.set_xlim(5_000, 62_000)
    ax.set_xticks(range(10_000, 61_000, 10_000))
    ax.set_xticklabels([miles(v) for v in range(10_000, 61_000, 10_000)])
    ax.set_xlabel("USD")
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)

    from matplotlib.lines import Line2D

    leyenda = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=azul,
            markersize=8,
            label=f"Nuestros precios pedidos ({FECHA_DATOS})",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="none",
            markerfacecolor=naranja,
            markersize=7,
            label=f"Promedio orientativo externo ({FUENTE})",
        ),
        Line2D([0], [0], color=naranja, linewidth=6, alpha=0.25, label="Banda publicada por la fuente"),
    ]
    ax.legend(handles=leyenda, loc="lower right", frameon=True, fontsize=8.2, framealpha=0.95)

    fig.text(
        0.01,
        0.985,
        "Precios pedidos en La Habana frente a la referencia externa",
        fontsize=13,
        fontweight="bold",
        va="top",
    )
    fig.text(
        0.01,
        0.945,
        "Mediana de Revolico en USD por municipio. La referencia externa es un promedio orientativo "
        "de una fuente comercial,\nno un precio de transaccion: la comparacion indica orden de magnitud, no una medicion de la brecha.",
        fontsize=8.6,
        color="#444444",
        va="top",
    )
    fig.text(
        0.01,
        0.015,
        "Cotorro se excluye de la figura (n=2 < 5). En Playa la referencia cubre Miramar y Siboney, no el municipio completo; "
        "en Plaza de la Revolucion cubre Vedado.\n"
        "Nuestros datos son precios pedidos, no precios pactados. Fuente externa citada como contexto en fuentes_externas.md.",
        fontsize=7.6,
        color="#666666",
    )
    fig.subplots_adjust(top=0.83, bottom=0.17, left=0.22, right=0.98)

    ruta_png = nueva_ruta_salida(OUT, "08_contraste_fuentes_externas.png")
    fig.savefig(ruta_png, dpi=200)
    plt.close(fig)
    print(f"Escrito {ruta_png}")
    print()
    print(datos[["municipio", "n_revolico", "mediana_revolico", "referencia_min", "referencia_max", "diferencia_pct"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
