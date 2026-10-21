"""Revisa los anuncios con precio de analisis < 1000 (umbral de 'precio raro').

Genera `outputs/validacion/revision_precios_bajos_1000.csv` y consulta la ficha
individual de cada anuncio (Revolico y Cubisima) para buscar el precio real en
la descripcion, el titulo o el campo de precio de la pagina. No modifica el
maestro ni las fuentes originales.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from precio_moneda import precios_analisis
from revisar_descripciones_precios_bajos import HEADERS, ESPERA, montos_en_descripcion, obtener

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "validacion"
UMBRAL = 1000


def main() -> None:
    maestro_path = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))[-1]
    maestro = pd.read_csv(maestro_path, dtype=str).fillna("")
    maestro["precio_analisis"], maestro["moneda_analisis"] = precios_analisis(maestro)
    maestro["precio_analisis"] = pd.to_numeric(maestro["precio_analisis"], errors="coerce")
    maestro["precio_original"] = pd.to_numeric(maestro["precio_original"], errors="coerce")

    bajos = maestro[maestro["precio_analisis"] < UMBRAL].copy()
    lista = bajos[
        ["fuente", "id_local", "url", "precio_original", "moneda", "moneda_analisis", "titulo"]
    ].reset_index(drop=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ruta_lista = OUT_DIR / "revision_precios_bajos_1000.csv"
    lista.to_csv(ruta_lista, index=False, encoding="utf-8-sig")
    print(f"Lista de revision: {ruta_lista} ({len(lista)} anuncios)")

    registros = []
    sesion = requests.Session()
    for numero, fila in enumerate(lista.itertuples(index=False), start=1):
        datos = obtener(fila.url, sesion)
        registro = {
            "numero": numero,
            "fuente": fila.fuente,
            "id_local": fila.id_local,
            "titulo": fila.titulo,
            "precio_publicado": fila.precio_original,
            "moneda_publicada": fila.moneda,
            "url": fila.url,
            **datos,
        }
        registro["montos_en_descripcion"] = montos_en_descripcion(registro.get("descripcion", ""))
        registros.append(registro)
        print(
            f"[{numero:02d}/{len(lista)}] {registro.get('estado', ''):<12} "
            f"{str(registro.get('precio_pagina', '')):<12} {fila.url[:62]}"
        )
        time.sleep(ESPERA)

    tabla = pd.DataFrame(registros)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida_csv = OUT_DIR / f"revision_precios_bajos_1000_{marca}.csv"
    tabla.to_csv(salida_csv, index=False, encoding="utf-8-sig")

    lineas = [
        "# Revision de precios raros (< 1000 en precio de analisis)",
        "",
        f"- Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Anuncios: {len(tabla)}",
        "",
    ]
    for fila in tabla.to_dict("records"):
        lineas.append(f"## {fila['numero']:02d}. [{fila['fuente']}] {fila['precio_publicado']} {fila['moneda_publicada']}")
        lineas.append(f"- URL: {fila['url']}")
        lineas.append(f"- Estado: {fila.get('estado', '')}")
        lineas.append(f"- Precio en la pagina: {fila.get('precio_pagina', '')}")
        lineas.append(f"- Titulo en la pagina: {fila.get('titulo_pagina', '')}")
        lineas.append(f"- Montos en la descripcion: {fila.get('montos_en_descripcion', '') or 'ninguno'}")
        lineas.append(f"- Descripcion: {fila.get('descripcion', '') or 'sin descripcion'}")
        lineas.append("")
    salida_md = OUT_DIR / f"revision_precios_bajos_1000_{marca}.md"
    salida_md.write_text("\n".join(lineas), encoding="utf-8")
    print(f"CSV: {salida_csv}")
    print(f"MD : {salida_md}")


if __name__ == "__main__":
    main()
