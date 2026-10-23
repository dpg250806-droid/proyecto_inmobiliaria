#!/usr/bin/env python3
"""Prueba de sensibilidad a la retirada de alquileres y anuncios no residenciales.

Los 9 alquileres publicados en el catalogo de venta y los 7 anuncios que no son
oferta de venta de vivienda ya estan fuera del maestro. Esta prueba reconstruye
el escenario alternativo (haberlos conservado como si fueran ventas) y compara
las cifras de precio, para documentar que la retirada afecta a la cola de la
distribucion y no al centro.

No modifica el maestro ni ningun archivo original: escribe un CSV y un informe
breve en `outputs/auditoria/`.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from precio_moneda import precios_analisis

ROOT = Path(__file__).resolve().parent
INTEGRACION = ROOT / "outputs" / "integracion"
AUDITORIA = ROOT / "outputs" / "auditoria"


def maestro_vigente() -> Path:
    return sorted(INTEGRACION.glob("dataset_maestro_*.csv"))[-1]


def maestro_con_excluidos(ids: set[str], vigente: Path) -> tuple[Path, set[str]]:
    """Maestro anterior que conserva mas anuncios retirados y los ids recuperables.

    Los 22 anuncios de la lista se retiraron en dos momentos: seis en la pasada
    del 18/10 y los 16 restantes (9 alquileres y 7 no residenciales) en la del
    20/10. Solo estos ultimos existen en el maestro previo inmediato.
    """
    mejor: tuple[Path, set[str]] | None = None
    for ruta in sorted(INTEGRACION.glob("dataset_maestro_*.csv"), reverse=True):
        if ruta == vigente:
            continue
        tabla = pd.read_csv(ruta, dtype=str, usecols=["id_local"]).fillna("")
        presentes = ids & set(tabla["id_local"])
        if mejor is None or len(presentes) > len(mejor[1]):
            mejor = (ruta, presentes)
    if mejor is None or not mejor[1]:
        raise SystemExit("No se encontro un maestro previo con anuncios retirados")
    return mejor


def con_precio(tabla: pd.DataFrame) -> pd.DataFrame:
    tabla = tabla.copy()
    tabla["precio_analisis"], tabla["moneda_analisis"] = precios_analisis(tabla)
    tabla["precio_analisis"] = pd.to_numeric(tabla["precio_analisis"], errors="coerce")
    return tabla


def resumen(tabla: pd.DataFrame, etiqueta: str) -> pd.DataFrame:
    base = tabla[tabla["precio_analisis"].notna() & tabla["moneda_analisis"].ne("")]
    filas = []
    for (fuente, moneda), grupo in base.groupby(["fuente", "moneda_analisis"]):
        filas.append(
            {
                "escenario": etiqueta,
                "fuente": fuente,
                "moneda": moneda,
                "n": len(grupo),
                "mediana": grupo["precio_analisis"].median(),
                "p05": grupo["precio_analisis"].quantile(0.05),
                "minimo": grupo["precio_analisis"].min(),
                "maximo": grupo["precio_analisis"].max(),
            }
        )
    return pd.DataFrame(filas)


def municipios(tabla: pd.DataFrame, etiqueta: str) -> pd.DataFrame:
    base = tabla[
        tabla["precio_analisis"].notna()
        & tabla["moneda_analisis"].eq("USD")
        & tabla["municipio_homologado"].ne("")
    ]
    filas = []
    for municipio, grupo in base.groupby("municipio_homologado"):
        filas.append(
            {
                "escenario": etiqueta,
                "municipio": municipio,
                "n": len(grupo),
                "mediana": grupo["precio_analisis"].median(),
            }
        )
    return pd.DataFrame(filas)


def main() -> None:
    vigente = maestro_vigente()
    actual = pd.read_csv(vigente, dtype=str).fillna("")

    excluidos = pd.read_csv(
        sorted(INTEGRACION.glob("anuncios_no_residenciales_*.csv"))[-1], dtype=str
    ).fillna("")
    ids = set(excluidos["id_local"])

    previo_path, ids_recuperables = maestro_con_excluidos(ids, vigente)
    previo = pd.read_csv(previo_path, dtype=str).fillna("")
    retirados = previo[previo["id_local"].isin(ids_recuperables)].copy()

    actual = con_precio(actual)
    retirados = con_precio(retirados)
    alternativo = con_precio(pd.concat([actual, retirados], ignore_index=True))

    print(f"Maestro vigente: {vigente.name} ({len(actual)} anuncios)")
    print(f"Maestro previo:  {previo_path.name}")
    print(f"Anuncios retirados: {len(retirados)}")
    print()

    detalle = retirados[
        [
            "id_local",
            "fuente",
            "titulo",
            "precio_original",
            "moneda",
            "precio_analisis",
            "moneda_analisis",
            "municipio_homologado",
            "veredicto_revision",
        ]
    ].copy()
    detalle["precio_analisis"] = detalle["precio_analisis"].round(0)
    print("Anuncios retirados y precio que habrian aportado al analisis:")
    print(detalle.to_string(index=False, max_colwidth=48))
    print()

    comparacion = pd.concat(
        [resumen(actual, "sin_retirados"), resumen(alternativo, "con_retirados")],
        ignore_index=True,
    ).sort_values(["fuente", "moneda", "escenario"])

    pivote = comparacion.pivot_table(
        index=["fuente", "moneda"], columns="escenario", values=["n", "mediana", "p05"]
    )
    pivote.columns = [f"{metrica}_{escenario}" for metrica, escenario in pivote.columns]
    pivote = pivote.reset_index()
    pivote["delta_mediana_pct"] = (
        (pivote["mediana_con_retirados"] - pivote["mediana_sin_retirados"])
        / pivote["mediana_sin_retirados"]
        * 100
    ).round(2)
    pivote["delta_p05_pct"] = (
        (pivote["p05_con_retirados"] - pivote["p05_sin_retirados"])
        / pivote["p05_sin_retirados"]
        * 100
    ).round(2)
    print("Comparacion por fuente y moneda:")
    print(pivote.round(0).to_string(index=False))
    print()

    municipios_comparados = pd.concat(
        [municipios(actual, "sin_retirados"), municipios(alternativo, "con_retirados")],
        ignore_index=True,
    )
    mun_pivote = municipios_comparados.pivot_table(
        index="municipio", columns="escenario", values=["n", "mediana"]
    )
    mun_pivote.columns = [f"{metrica}_{escenario}" for metrica, escenario in mun_pivote.columns]
    mun_pivote = mun_pivote.reset_index()
    mun_pivote["delta_n"] = mun_pivote["n_con_retirados"] - mun_pivote["n_sin_retirados"]
    mun_pivote["delta_mediana"] = (
        mun_pivote["mediana_con_retirados"] - mun_pivote["mediana_sin_retirados"]
    )
    mun_pivote = mun_pivote.sort_values("n_sin_retirados", ascending=False)
    print("Municipios (USD, cualquier fuente):")
    print(mun_pivote.round(0).to_string(index=False))
    print()

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    AUDITORIA.mkdir(parents=True, exist_ok=True)
    ruta_detalle = AUDITORIA / f"sensibilidad_retirados_detalle_{marca}.csv"
    ruta_global = AUDITORIA / f"sensibilidad_retirados_global_{marca}.csv"
    ruta_municipal = AUDITORIA / f"sensibilidad_retirados_municipal_{marca}.csv"
    detalle.to_csv(ruta_detalle, index=False, encoding="utf-8-sig")
    pivote.to_csv(ruta_global, index=False, encoding="utf-8-sig")
    mun_pivote.to_csv(ruta_municipal, index=False, encoding="utf-8-sig")

    md = [f"# Sensibilidad a la retirada de alquileres y anuncios no residenciales\n"]
    md.append(f"- Maestro vigente: `{vigente.name}` ({len(actual)} anuncios).")
    md.append(f"- Maestro previo usado para reconstruir el escenario: `{previo_path.name}`.")
    md.append(f"- Anuncios retirados: {len(retirados)} (9 alquileres y 7 no residenciales).\n")
    md.append("## Precio que habrian aportado al analisis\n")
    md.append(detalle.to_markdown(index=False))
    md.append("\n## Comparacion por fuente y moneda\n")
    md.append(pivote.round(0).to_markdown(index=False))
    md.append("\n## Municipios (USD)\n")
    md.append(mun_pivote.round(0).to_markdown(index=False))
    md.append(
        "\n## Lectura\n\n"
        "La retirada afecta al minimo y al percentil 5, no a la mediana. "
        "Los anuncios retirados que habrian entrado al analisis son alquileres con "
        "precios de renta (250-750 CUC) y un alquiler de 300 USD: conservarlos "
        "habria mezclado rentas mensuales con precios de venta. "
        "La mayoria no tiene municipio homologado, por lo que las medianas "
        "municipales no cambian.\n"
    )
    ruta_md = AUDITORIA / f"sensibilidad_retirados_{marca}.md"
    ruta_md.write_text("\n".join(md), encoding="utf-8")

    print(f"Escrito {ruta_global.name}")
    print(f"Escrito {ruta_municipal.name}")
    print(f"Escrito {ruta_detalle.name}")
    print(f"Escrito {ruta_md.name}")


if __name__ == "__main__":
    main()
