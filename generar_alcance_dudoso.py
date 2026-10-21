#!/usr/bin/env python3
"""Genera `revision_manual/alcance_dudoso.csv`.

Lista los anuncios que se conservan en el maestro pese a tener un alcance dudoso
(uso mixto vivienda-negocio, fincas, almacenes, hostales). Decision de la
investigadora (20/10/2026): todo lo que sea venta de inmueble es valido, asi
que las 14 fichas se **mantienen en el analisis** y quedan marcadas para poder
medir su sensibilidad.

El emparejamiento se hace por el prefijo del identificador local de Revolico
y se verifica contra la URL exacta del maestro. No modifica el maestro.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT = ROOT / "revision_manual" / "alcance_dudoso.csv"

CASOS = {
    "rev_000773": (
        "local_adaptado",
        "El titulo dice 'local adaptado a vivienda con principio de papeles'; uso y situacion legal no verificables.",
    ),
    "rev_000314": (
        "hostal",
        "El titulo y la descripcion lo presentan como hostal en Casco Historico; puede incluir vivienda, pero el uso principal es negocio.",
    ),
    "rev_000528": (
        "uso_mixto",
        "Casa hostal con restaurante 'con todo adentro'; el precio puede incluir negocio, mobiliario o licencia.",
    ),
    "rev_000717": (
        "casa_restaurante",
        "Casa-restaurante de dos plantas; uso mixto vivienda/negocio.",
    ),
    "rev_000458": (
        "casa_con_bar",
        "Casa en 10 de Octubre 'con bar incluido'; uso mixto.",
    ),
    "rev_000653": (
        "almacen",
        "Casa grande para almacen de 240 m2; el uso declarado no es vivienda principal.",
    ),
    "rev_000229": (
        "finca",
        "Finca/asienda en Arroyo Naranjo; puede incluir vivienda, pero el objeto principal es tierra/negocio.",
    ),
    "rev_000491": (
        "finca",
        "Finca en venta; no se especifica si la vivienda es parte del precio.",
    ),
    "rev_000537": (
        "finca",
        "Venta de finca en Boyeros; uso agricola/terreno.",
    ),
    "rev_000561": (
        "finca",
        "Finca 'con todo adentro' en El Chico; posible negocio en funcionamiento.",
    ),
    "rev_000590": (
        "finca",
        "Vendo finca en Alamar; terreno/uso agricola, no vivienda tipica.",
    ),
    "rev_000594": (
        "finca",
        "Finca de 2 hectareas cerca de la UCI con vivienda y laguna; el precio incluye tierra y otros activos.",
    ),
    "rev_000184": (
        "casa_con_finca",
        "Casa con finca en Lawton; uso mixto vivienda/terreno.",
    ),
    "rev_000683": (
        "uso_mixto",
        "Propiedad habilitada para restaurante y casa en Vedado; uso mixto.",
    ),
}

FECHA_REVISION = "2026-10-19"
FECHA_DECISION = "2026-10-20"
DECISION = "incluido_en_analisis"
NOTA_DECISION = (
    "Decision de la investigadora (20/10/2026): todo lo que sea venta de inmueble es valido, "
    "por lo que el anuncio se mantiene en el analisis. La marca solo permite medir la "
    "sensibilidad de los resultados a estas 14 fichas."
)
CAVEAT = {
    "finca": "El precio puede incluir tierra y otros activos, no solo vivienda.",
    "casa_con_finca": "El precio puede incluir la finca, no solo la vivienda.",
    "uso_mixto": "El precio puede incluir el negocio en funcionamiento.",
    "hostal": "El precio puede incluir la licencia y el equipamiento del negocio.",
    "casa_restaurante": "El precio puede incluir el equipamiento del restaurante.",
    "casa_con_bar": "El precio puede incluir la licencia del bar.",
    "almacen": "El uso declarado no es vivienda principal.",
    "local_adaptado": "El uso y la situacion legal no son verificables.",
}


def main() -> None:
    maestro_path = sorted(MASTER_DIR.glob("dataset_maestro_*.csv"))[-1]
    maestro = pd.read_csv(maestro_path, dtype=str).fillna("")

    filas = []
    for prefijo, (motivo, evidencia) in CASOS.items():
        coincidencia = maestro[maestro["id_local"].str.startswith(prefijo)]
        if len(coincidencia) != 1:
            raise SystemExit(
                f"Se esperaba exactamente un anuncio para {prefijo} y hay {len(coincidencia)}"
            )
        fila = coincidencia.iloc[0]
        filas.append(
            {
                "fuente": fila["fuente"],
                "id_local": fila["id_local"],
                "url": fila["url"],
                "motivo": motivo,
                "evidencia": evidencia,
                "titulo": fila["titulo"],
                "fecha_revision": FECHA_REVISION,
                "estado": DECISION,
                "fecha_decision": FECHA_DECISION,
                "decisor": "investigadora",
                "nota": NOTA_DECISION,
                "caveat_analisis": CAVEAT.get(motivo, ""),
            }
        )

    salida = pd.DataFrame(filas)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Escrito {OUT} con {len(salida)} filas")
    print(salida[["id_local", "motivo", "estado", "titulo"]].to_string(index=False))


if __name__ == "__main__":
    main()
