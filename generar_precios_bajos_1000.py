#!/usr/bin/env python3
"""Genera `revision_manual/precios_bajos_1000.csv`.

Revision manual (20/10/2026) de los anuncios con precio de analisis < 1.000
(umbral de "precio raro") y de los alquileres detectados en el catalogo de
venta. Para cada anuncio se consulto la ficha individual (Cubisima y Revolico)
y se leyo la descripcion completa; el veredicto queda con su evidencia.

Veredictos usados:
- `alquiler`: el anuncio ofrece un alquiler, no una venta -> sale del maestro.
- `no_verificable`: el precio publicado no es verificable -> el anuncio se
  conserva y queda sin precio de analisis.
- `despublicado`: el anuncio ya no esta accesible -> sin precio de analisis.
- `precio_recuperado`: el precio real esta en la descripcion -> se reextrae.

No modifica el maestro ni las fuentes originales.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "revision_manual" / "precios_bajos_1000.csv"
FECHA = "2026-10-20"

# (id_local, veredicto, precio_en_descripcion, moneda_en_descripcion, estado, observacion)
CASOS = [
    # --- Cubisima: alquileres publicados en el catalogo de venta ---
    (
        "cubisima_000259",
        "alquiler",
        "",
        "",
        "publicado",
        "La descripcion dice 'CASA EN LA HABANA ... 500 USD SE RENTA Casa de renta en la Habana vieja'. "
        "Es un alquiler, no una venta: el precio publicado es la renta.",
    ),
    (
        "cubisima_000316",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: 'Rento apartamentos amueblado totalmente'. Alquiler, no venta.",
    ),
    (
        "cubisima_000337",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: 'Renta de por tiempo indefinido ... Costo mensual: 700 USD'. "
        "El precio publicado es la renta mensual.",
    ),
    (
        "cubisima_000353",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: 'disponible para alquiler de por temporadas ... El alquiler mensual es de 900 euros'. "
        "Alquiler, no venta.",
    ),
    (
        "cubisima_000428",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: 'Apartamento Capitalista independiente Completo CUARTO ... No NIÑOS NO mascotas ... "
        "por DIAS por HORAS y MESES'. Alquiler turistico, no venta.",
    ),
    (
        "cubisima_000504",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: '*RENTA LINEAL* ... Precio 330 USD mensual'. Alquiler, no venta.",
    ),
    (
        "cubisima_000554",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: 'Precio es 300 usd/ mes para alquiler de 6 meses o mas'. Alquiler, no venta.",
    ),
    (
        "cubisima_000577",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: '*RENTA LINEAL EN PLAYA* ... *Precio: 300 USD mensual*'. Alquiler, no venta.",
    ),
    # --- Cubisima: precio publicado no verificable ---
    (
        "cubisima_000025",
        "no_verificable",
        "",
        "",
        "publicado",
        "Apartamento en Miramar (4 habitaciones, 3 banos, garaje, elevador) que se vende o se permuta. "
        "El precio publicado (190) no aparece en la descripcion y es compatible con un importe truncado "
        "(precedente: '18.00' con descripcion '18 000 usd'). No se imputa precio.",
    ),
    (
        "cubisima_000144",
        "no_verificable",
        "",
        "",
        "publicado",
        "Descripcion: 'Excelente apartamento en zona privilegiada del vedado, muy seguro y muy tranquilo'. "
        "Sin precio en el texto; el importe publicado no es verificable.",
    ),
    (
        "cubisima_000304",
        "no_verificable",
        "",
        "",
        "publicado",
        "Ficha sin descripcion: no hay forma de verificar el importe publicado.",
    ),
    (
        "cubisima_000583",
        "no_verificable",
        "",
        "",
        "publicado",
        "Misma plantilla que un alquiler por dias/horas/meses ('Apartamento Capitalista independiente Completo "
        "CUARTO ... telefono No NIÑOS NO mascotas') sin precio en el texto. Se conserva el anuncio y se le "
        "deja el precio sin verificar.",
    ),
    (
        "cubisima_000217",
        "no_verificable",
        "",
        "",
        "publicado",
        "Casa colonial de 400 m2 con 8 habitaciones; el precio publicado (1) es un marcador y la descripcion "
        "no declara importe.",
    ),
    # --- Revolico ---
    (
        "rev_000163",
        "precio_recuperado",
        "12500",
        "USD",
        "publicado",
        "La descripcion dice 'Precio: 12,500' (coma de millares). El precio publicado (125) es la lectura "
        "erronea de '12,5' con coma decimal; el precio real es 12.500 USD.",
    ),
    (
        "rev_000294",
        "alquiler",
        "",
        "",
        "publicado",
        "Descripcion: 'se rebaja poco a poco del pago de la renta'. Es un alquiler, no una venta.",
    ),
    (
        "rev_000289",
        "no_verificable",
        "",
        "",
        "publicado",
        "Precio publicado 111 (marcador habitual de 'precio a concertar'); la descripcion no menciona importe.",
    ),
    (
        "rev_000291",
        "no_verificable",
        "",
        "",
        "publicado",
        "Precio publicado 111 (marcador habitual de 'precio a concertar'); la descripcion no menciona importe.",
    ),
    (
        "rev_000599",
        "no_verificable",
        "",
        "",
        "publicado",
        "Precio 123 con 'Precio : me ajusto con dinero en mano'; no hay importe en el texto.",
    ),
    (
        "rev_000600",
        "no_verificable",
        "",
        "",
        "publicado",
        "Precio 123 con 'Precio : me ajusto con dinero en mano'; no hay importe en el texto.",
    ),
    (
        "rev_000276",
        "despublicado",
        "",
        "",
        "despublicado",
        "Anuncio ya despublicado (comprobado el 20/10/2026). El titulo dice '14,5 USD' (14.500 USD) y no hay "
        "forma de verificarlo.",
    ),
    (
        "rev_000297",
        "despublicado",
        "",
        "",
        "despublicado",
        "Anuncio despublicado (20/10/2026) y sin descripcion: '350' puede ser 35.000 y no es verificable.",
    ),
    (
        "rev_000686",
        "despublicado",
        "",
        "",
        "despublicado",
        "Anuncio despublicado (20/10/2026): '150' no es verificable.",
    ),
    (
        "rev_000693",
        "despublicado",
        "",
        "",
        "despublicado",
        "Anuncio despublicado (20/10/2026): '150' no es verificable.",
    ),
]


def main() -> None:
    maestro_path = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))[-1]
    maestro = pd.read_csv(maestro_path, dtype=str).fillna("")
    maestro["precio_original"] = pd.to_numeric(maestro["precio_original"], errors="coerce")

    filas = []
    for numero, (id_local, veredicto, precio_desc, moneda_desc, estado, observacion) in enumerate(
        CASOS, start=1
    ):
        coincidencia = maestro[maestro["id_local"].eq(id_local)]
        if coincidencia.empty:
            # En Revolico el id_local lleva la URL detras del prefijo corto.
            coincidencia = maestro[maestro["id_local"].str.startswith(id_local + "_")]
        if coincidencia.empty:
            raise SystemExit(f"{id_local} no esta en el maestro {maestro_path.name}")
        fila = coincidencia.iloc[0]
        filas.append(
            {
                "numero": numero,
                "fuente": fila["fuente"],
                "id_local": id_local,
                "url": fila["url"],
                "veredicto": veredicto,
                "precio_titulo": fila["precio_original"],
                "moneda_titulo": fila["moneda"],
                "precio_pagina": "",
                "precio_en_descripcion": precio_desc,
                "moneda_en_descripcion": moneda_desc,
                "municipio": fila["municipio_homologado"],
                "estado": estado,
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
