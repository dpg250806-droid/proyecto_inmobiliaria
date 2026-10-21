#!/usr/bin/env python3
"""Genera `revision_manual/precios_pendientes_recuperados.csv`.

Segunda pasada sobre los 134 anuncios que estaban sin precio de analisis
(20/10/2026). Para cada uno se leyo el texto completo ya descargado (ficha de
Cubisima cacheada y descripcion de la pagina de Revolico) buscando el precio
declarado con un criterio mas laxo que el del primer script, que exigia una
moneda explicita y no miraba las frases con "mil", "K" ni los digitos con
emojis.

Decisiones:
- `precio_recuperado`: el texto declara el importe y la moneda -> se reextrae
  con su cita literal.
- `otro` / `producto`: el anuncio no es una oferta de venta de vivienda
  (empresa de servicios, producto industrial, anuncio de agencia o demanda de
  compra) -> sale del maestro de ventas.
- El resto no cambia: el vendedor no publico precio y no se imputa ninguno.

No modifica el maestro ni las fuentes originales.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "revision_manual" / "precios_pendientes_recuperados.csv"
FECHA = "2026-10-20"

# (id_local, veredicto, precio, moneda, observacion)
CASOS = [
    # --- Precios recuperados del texto ---
    (
        "cubisima_000276",
        "precio_recuperado",
        "13000",
        "USD",
        "Descripcion: 'SE PUEDE PAGAR EN EL EXTERIOR ... 13000 USD Contáctenos al 53029174'. "
        "El precio publicado (1 CUC) no era el precio de venta.",
    ),
    (
        "cubisima_000552",
        "precio_recuperado",
        "9000",
        "USD",
        "Descripcion: 'El apartamento lo vendo en 9000 usd y me ajusto a 8000 usd'. Se toma el precio "
        "pedido (9.000 USD); los 8.000 son el suelo de negociacion.",
    ),
    (
        "cubisima_000217",
        "precio_recuperado",
        "600000",
        "USD",
        "Descripcion: 'El precio de $600000 or € aun es negociable'. Casa colonial de 400 m2 con 8 "
        "habitaciones en Vedado; el precio publicado (1 CUC) era un marcador.",
    ),
    (
        "cubisima_000311",
        "precio_recuperado",
        "25000",
        "USD",
        "Descripcion: 'se vende con casi todo en 25 mil o en 20'. Se toma el importe pedido (25 mil).",
    ),
    (
        "cubisima_000469",
        "precio_recuperado",
        "30000",
        "USD",
        "Descripcion: 'PRECIO 30MIL USD POR LA CASA SOLO VERDADEROS INTERESADOS'. Casa de 178 m2 en "
        "Vedado que necesita reparaciones.",
    ),
    (
        "cubisima_000556",
        "precio_recuperado",
        "70000",
        "USD",
        "Descripcion: '70 mil dollares, se puede pagar una parte en cuba y la otra en USA'. Casa de 4 "
        "cuartos en Siboney.",
    ),
    (
        "rev_000579",
        "precio_recuperado",
        "20000",
        "USD",
        "Descripcion: 'Precio:20000usd' (C&J HOUSE, casa en La Cumbre con 3 cuartos).",
    ),
    (
        "rev_000151",
        "precio_recuperado",
        "4500",
        "USD",
        "Descripcion: 'Precio: USD $4,500'. Casa de dos niveles en Mantilla (Arroyo Naranjo).",
    ),
    (
        "rev_000372",
        "precio_recuperado",
        "125000",
        "EUR",
        "Descripcion: 'Precio: solo 1️⃣2️⃣5️⃣0️⃣0️⃣0️⃣ Euro'. Apartamento de 147 m2 frente al Malecon en "
        "Vedado. La moneda se conserva en euros porque el texto la declara.",
    ),
    (
        "rev_000671",
        "precio_recuperado",
        "35000",
        "USD",
        "Descripcion: 'Precio: 35 mil usd'. Casa independiente en Santo Suarez.",
    ),
    (
        "rev_000674",
        "precio_recuperado",
        "20000",
        "USD",
        "Descripcion: 'Precio de rebaja: 20 mil usd'. Apartamento en el Sevillano.",
    ),
    (
        "rev_000679",
        "precio_recuperado",
        "25000",
        "USD",
        "Descripcion: 'Nuevo precio: REBAJA a 25 000 / Precio original: 28 000'. Propiedad independiente "
        "en Lawton; se toma el precio rebajado.",
    ),
    (
        "rev_000544",
        "precio_recuperado",
        "35000",
        "USD",
        "Descripcion: 'Precio: 35 mil usd' (Nexo Inmobal, apartamento en Villa Panamericana).",
    ),
    (
        "rev_000555",
        "precio_recuperado",
        "70000",
        "USD",
        "Descripcion: 'CASA EN BAJOS, EN PLAYA, ATABEY PRECIO : 70 MIL USD'.",
    ),
    (
        "rev_000084",
        "precio_recuperado",
        "7500",
        "USD",
        "El titulo dice '7,5 USD' y la pagina muestra 7.5 USD: por la convencion de separadores de "
        "millares del sector (mismo criterio que '12,5 USD' -> 12.500 USD) el importe es 7.500 USD. "
        "La descripcion confirma que el precio es negociable.",
    ),
    # --- No son oferta de venta de vivienda: salen del maestro ---
    (
        "rev_000055",
        "producto",
        "",
        "",
        "Anuncio de una empresa de soluciones en metal ('Somos una empresa de soluciones en metal "
        "... 77661394 53882209'). No es una vivienda en venta.",
    ),
    (
        "rev_000203",
        "producto",
        "",
        "",
        "Anuncio de producto: 'Tiras de cabillas de polimero reforzado'. No es una vivienda en venta.",
    ),
    (
        "rev_000139",
        "otro",
        "",
        "",
        "Anuncio de servicios de una inmobiliaria ('Si vas a VENDER: tasacion profesional, promocion "
        "activa...'). No es una vivienda en venta.",
    ),
    (
        "rev_000578",
        "otro",
        "",
        "",
        "Anuncio de una agencia de gestion de ventas ('Gestores especializados en venta de casas ... "
        "Cobramos el 3% del valor de venta'). No es una vivienda en venta.",
    ),
    (
        "rev_000749",
        "otro",
        "",
        "",
        "Anuncio de una agencia ('QUIERES VENDER TU PROPIEDAD MAS RAPIDO?'). No es una vivienda en venta.",
    ),
    (
        "rev_000128",
        "otro",
        "",
        "",
        "Es una demanda de compra ('Compro casa o apartamento en Guanabacoa o Regla'), no una oferta "
        "de venta.",
    ),
    (
        "cubisima_000211",
        "otro",
        "",
        "",
        "La descripcion vende un negocio: 'Se vende restaurante incluyendo mipyme 120 metros cuadrados 3 "
        "salones ... 12 mesas para 40 personas'. No es una vivienda en venta.",
    ),
]


def main() -> None:
    maestro_path = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))[-1]
    maestro = pd.read_csv(maestro_path, dtype=str).fillna("")
    maestro["precio_original"] = pd.to_numeric(maestro["precio_original"], errors="coerce")

    filas = []
    for numero, (id_local, veredicto, precio, moneda, observacion) in enumerate(CASOS, start=1):
        coincidencia = maestro[maestro["id_local"].eq(id_local)]
        if coincidencia.empty:
            coincidencia = maestro[maestro["id_local"].str.startswith(id_local + "_")]
        if coincidencia.empty:
            raise SystemExit(f"{id_local} no esta en el maestro {maestro_path.name}")
        fila = coincidencia.iloc[0]
        filas.append(
            {
                "numero": numero,
                "fuente": fila["fuente"],
                "id_local": fila["id_local"],
                "url": fila["url"],
                "veredicto": veredicto,
                "precio_titulo": fila["precio_original"],
                "moneda_titulo": fila["moneda"],
                "precio_pagina": "",
                "precio_en_descripcion": precio,
                "moneda_en_descripcion": moneda,
                "municipio": fila["municipio_homologado"],
                "estado": "publicado",
                "observacion": observacion,
                "fecha_revision": FECHA,
            }
        )

    salida = pd.DataFrame(filas)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Escrito {OUT} con {len(salida)} filas")
    print(salida["veredicto"].value_counts().to_string())


if __name__ == "__main__":
    main()
