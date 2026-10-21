"""Detecta anuncios de alquiler publicados en catalogos de venta (solo lectura).

Usa las descripciones ya descargadas de Revolico y, para Cubisima, consulta la
ficha individual de cada anuncio. Marca los casos en los que el texto dice
expresamente que se alquila (no es una oferta de venta).
"""
from __future__ import annotations

import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from precio_moneda import precios_analisis
from revisar_descripciones_precios_bajos import ESPERA, obtener

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "validacion"

PATRONES_ALQUILER = [
    re.compile(r"\bse\s+(?:renta|alquila|alquiler)\b", re.IGNORECASE),
    re.compile(r"\brenta\s+(?:lineal|por\s+tiempo|de\s+por)\b", re.IGNORECASE),
    re.compile(r"\balquiler\s+mensual\b", re.IGNORECASE),
    re.compile(r"\bprecio\s+(?:es\s+)?[\d.,]+\s*(?:usd|eur|\$|€)?\s*(?:/\s*mes|/mes|al\s+mes|mensual)\b", re.IGNORECASE),
    re.compile(r"\busd\s*(?:/\s*mes|/mes)\b", re.IGNORECASE),
    re.compile(r"\bpor\s+d[ií]as\b", re.IGNORECASE),
    re.compile(r"\b(?:rento|renta)\b[^.]{0,40}\b(?:apartamento|casa|propiedad)\b", re.IGNORECASE),
    re.compile(r"\b(?:alquilo|alquiler)\b", re.IGNORECASE),
    re.compile(r"\bpago\s+de\s+la\s+renta\b", re.IGNORECASE),
    re.compile(r"\bpermuta\b", re.IGNORECASE),
    re.compile(r"\bse\s+permuta\b", re.IGNORECASE),
]


def frases_alquiler(texto: str) -> str:
    if not isinstance(texto, str) or not texto.strip():
        return ""
    hallazgos = []
    for patron in PATRONES_ALQUILER:
        for coincidencia in patron.finditer(texto):
            inicio = max(0, coincidencia.start() - 70)
            fin = min(len(texto), coincidencia.end() + 70)
            trozo = re.sub(r"\s+", " ", texto[inicio:fin]).strip()
            if trozo and trozo not in hallazgos:
                hallazgos.append(trozo)
    return " | ".join(hallazgos[:4])


def main() -> None:
    maestro_path = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))[-1]
    maestro = pd.read_csv(maestro_path, dtype=str).fillna("")
    maestro["precio_analisis"], maestro["moneda_analisis"] = precios_analisis(maestro)
    maestro["precio_analisis"] = pd.to_numeric(maestro["precio_analisis"], errors="coerce")

    modo = sys.argv[1] if len(sys.argv) > 1 else "revolico"

    if modo == "revolico":
        detalle = sorted((ROOT / "outputs" / "metadatos_revolico").glob("detalle_anuncios_revolico_*.csv"))[-1]
        textos = pd.read_csv(detalle, dtype=str).fillna("").drop_duplicates("url").set_index("url")["descripcion"]
        sub = maestro[maestro["fuente"].eq("Revolico")].copy()
        sub["descripcion"] = sub["url"].map(textos).fillna("")
        sub["indicio"] = sub["descripcion"].map(frases_alquiler)
        salida = sub[sub["indicio"].ne("")]
        print(f"Revolico: {len(salida)} anuncios con indicios de alquiler o permuta (de {len(sub)})")
        registros = salida[
            ["id_local", "titulo", "precio_original", "moneda", "precio_analisis", "moneda_analisis", "url", "indicio"]
        ]
    else:
        cache = OUT_DIR / "alquileres_cubisima_cache.csv"
        sub = maestro[maestro["fuente"].eq("Cubisima")].copy()
        if cache.exists():
            cache_df = pd.read_csv(cache, dtype=str).fillna("")
            textos = cache_df.drop_duplicates("url").set_index("url")
        else:
            textos = pd.DataFrame(columns=["url", "estado", "precio_pagina", "descripcion"])
        pendientes = [url for url in sub["url"] if url not in textos.index]
        print(f"Cubisima: {len(sub)} anuncios; {len(pendientes)} por consultar", flush=True)
        registros_extra = []
        sesion = requests.Session()
        for numero, url in enumerate(pendientes, start=1):
            datos = obtener(url, sesion)
            registros_extra.append({"url": url, **datos})
            if numero % 25 == 0:
                print(f"  {numero}/{len(pendientes)}", flush=True)
            time.sleep(ESPERA)
        nuevos = pd.DataFrame(registros_extra)
        if not textos.empty:
            nuevos = pd.concat([textos.reset_index(), nuevos], ignore_index=True)
        nuevos.to_csv(cache, index=False, encoding="utf-8-sig")
        mapa = nuevos.drop_duplicates("url").set_index("url")
        sub["descripcion"] = sub["url"].map(mapa["descripcion"]).fillna("")
        sub["estado_pagina"] = sub["url"].map(mapa["estado"]).fillna("")
        sub["precio_pagina"] = sub["url"].map(mapa["precio_pagina"]).fillna("")
        sub["indicio"] = sub["descripcion"].map(frases_alquiler)
        salida = sub[sub["indicio"].ne("")]
        print(f"Cubisima: {len(salida)} anuncios con indicios de alquiler o permuta (de {len(sub)})")
        registros = salida[
            ["id_local", "titulo", "precio_original", "moneda", "precio_analisis", "moneda_analisis",
             "estado_pagina", "precio_pagina", "url", "indicio"]
        ]

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida_csv = OUT_DIR / f"alquileres_{modo}_{marca}.csv"
    registros.to_csv(salida_csv, index=False, encoding="utf-8-sig")
    print(f"CSV: {salida_csv}")
    print(registros[["id_local", "precio_original", "moneda", "indicio"]].to_string(index=False, max_colwidth=90))


if __name__ == "__main__":
    main()
