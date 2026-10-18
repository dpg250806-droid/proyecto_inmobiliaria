#!/usr/bin/env python3
"""Abre los anuncios con precios bajos pendientes y extrae su descripcion real.

Para cada fila de `outputs/validacion/revision_precios_bajos.csv` consulta la URL
y guarda: estado del anuncio, precio publicado en la pagina, titulo, municipio y
descripcion literal, mas los montos de dinero mencionados dentro de la descripcion.

No modifica la lista de revision ni los CSV originales: genera un CSV y un MD
fechados en `outputs/validacion/`.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from html import unescape
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
LISTA = ROOT / "outputs" / "validacion" / "revision_precios_bajos.csv"
OUT_DIR = ROOT / "outputs" / "validacion"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TIMEOUT = 30
ESPERA = 0.7

MONEY_PATTERNS = [
    re.compile(r"\d[\d.,\s]{0,14}?\s*(?:usd|d[oó]lares?|cuc|cup|mlc|euros?|€)", re.I),
    re.compile(r"\b\d[\d.,]*\s*mil\b", re.I),
]


def limpiar(texto) -> str:
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def montos_en_descripcion(texto: str) -> str:
    """Devuelve fragmentos con dinero alrededor de cada monto encontrado."""
    fragmentos = []
    for patron in MONEY_PATTERNS:
        for coincidencia in patron.finditer(texto):
            inicio = max(0, coincidencia.start() - 25)
            fin = min(len(texto), coincidencia.end() + 15)
            fragmento = limpiar(texto[inicio:fin])
            if fragmento not in fragmentos:
                fragmentos.append(fragmento)
    return " | ".join(fragmentos[:6])


def campo_cubisima(html: str, etiqueta: str) -> str:
    patron = re.compile(
        r"<strong>\s*" + etiqueta + r"[^<]*</strong>\s*</div>\s*"
        r'<div class="col-lg-6">\s*(.*?)\s*</div>',
        re.S,
    )
    encontrado = patron.search(html)
    return limpiar(unescape(encontrado.group(1))) if encontrado else ""


def meta_cubisima(html: str, propiedad: str) -> str:
    """Extrae el contenido de una meta og:* de Cubisima."""
    indice = html.find(f"property='{propiedad}'")
    if indice == -1:
        indice = html.find(f'property="{propiedad}"')
    if indice == -1:
        return ""
    inicio = html.rfind("<meta content=", 0, indice)
    if inicio == -1:
        return ""
    coincidencia = re.search(r"content=['\"](.*)['\"]\s*$", html[inicio:indice], re.S)
    return unescape(coincidencia.group(1)) if coincidencia else ""


def descripcion_cubisima(html: str) -> str:
    """Devuelve la descripcion og:description de Cubisima."""
    return meta_cubisima(html, "og:description")


def revisar_cubisima(url: str, html: str) -> dict:
    descripcion = descripcion_cubisima(html)
    if not descripcion:
        otros = re.findall(r"<meta[^>]+name=['\"]description['\"][^>]*>", html)
        if otros:
            contenido = re.search(r"content=['\"](.*?)['\"]", otros[0], re.S)
            descripcion = unescape(contenido.group(1)) if contenido else ""
    return {
        "estado": "publicado",
        "precio_pagina": campo_cubisima(html, "Precio"),
        "titulo_pagina": limpiar(meta_cubisima(html, "og:title")),
        "municipio": campo_cubisima(html, "Ubicaci"),
        "fecha_pagina": campo_cubisima(html, "Publicaci"),
        "descripcion": limpiar(descripcion),
    }


def revisar_revolico(url: str, html: str) -> dict:
    coincidencia = re.search(r'<script[^>]*__NEXT_DATA__[^>]*>(.*?)</script>', html, re.S)
    if not coincidencia:
        if "Anuncio despublicado" in html:
            return {"estado": "despublicado"}
        return {"estado": "sin_datos"}
    datos = json.loads(coincidencia.group(1))
    props = datos.get("props", {}).get("pageProps", {})
    estado_pagina = props.get("__APOLLO_STATE__", {})
    anuncio = next(
        (valor for clave, valor in estado_pagina.items() if clave.startswith("AdType:")), None
    )
    if not anuncio:
        if "Anuncio despublicado" in html:
            return {"estado": "despublicado"}
        if props.get("errorCode"):
            return {"estado": f"anuncio_inexistente_{props['errorCode']}"}
        return {"estado": "sin_datos"}
    municipio_ref = (anuncio.get("municipality") or {}).get("__ref")
    provincia_ref = (anuncio.get("province") or {}).get("__ref")
    municipio = estado_pagina.get(municipio_ref, {}).get("name", "")
    provincia = estado_pagina.get(provincia_ref, {}).get("name", "")
    ubicacion = " ".join(parte for parte in (municipio, provincia) if parte)
    return {
        "estado": limpiar(anuncio.get("status", "")).lower() or "publicado",
        "precio_pagina": f"{anuncio.get('price')} {anuncio.get('currency')}".strip(),
        "titulo_pagina": limpiar(anuncio.get("title")),
        "municipio": limpiar(ubicacion),
        "fecha_pagina": limpiar(anuncio.get("updatedOnByUser")),
        "descripcion": limpiar(anuncio.get("description")),
    }


def obtener(url: str, sesion: requests.Session, intentos: int = 3) -> dict:
    html = ""
    for intento in range(intentos):
        try:
            respuesta = sesion.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.RequestException as error:
            if intento == intentos - 1:
                return {"estado": "error_http", "descripcion": str(error)}
            time.sleep(3)
            continue
        bloqueado = respuesta.status_code == 403 or "Just a moment" in respuesta.text[:2000]
        if respuesta.status_code == 200 and not bloqueado:
            html = respuesta.text
            break
        if intento == intentos - 1:
            return {"estado": f"http_{respuesta.status_code}"}
        time.sleep(3)
    if "revolico.com" in url:
        return revisar_revolico(url, html)
    return revisar_cubisima(url, html)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--espera", type=float, default=ESPERA, help="segundos entre peticiones")
    argumentos = parser.parse_args()

    if not LISTA.exists():
        raise SystemExit(f"No existe la lista de revision: {LISTA}")
    lista = pd.read_csv(LISTA, dtype=str).fillna("")

    registros = []
    for numero, fila in enumerate(lista.itertuples(index=False), start=1):
        datos = obtener(fila.url, requests.Session())
        registro = {
            "numero": numero,
            "fuente": fila.fuente,
            "id_local": fila.id_local,
            "precio_titulo": fila.precio_original,
            "moneda_titulo": fila.moneda,
            "url": fila.url,
            **datos,
        }
        registro["montos_en_descripcion"] = montos_en_descripcion(registro.get("descripcion", ""))
        registros.append(registro)
        print(
            f"[{numero:02d}/{len(lista)}] {registro['estado']:<14} "
            f"{registro.get('precio_pagina', ''):<10} {fila.url[:70]}"
        )
        time.sleep(argumentos.espera)

    tabla = pd.DataFrame(registros)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida_csv = OUT_DIR / f"revision_descripciones_{marca}.csv"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(salida_csv, index=False, encoding="utf-8-sig")

    lineas = ["# Revision de descripciones de precios bajos", ""]
    lineas.append(f"- Lista base: `{LISTA.name}` ({len(lista)} anuncios)")
    lineas.append(f"- Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lineas.append(f"- Estados: {dict(tabla['estado'].value_counts())}")
    lineas.append("")
    for fila in tabla.to_dict("records"):
        lineas.append(f"## {fila['numero']:02d}. [{fila['fuente']}] {fila['precio_titulo']} {fila['moneda_titulo']}")
        lineas.append(f"- URL: {fila['url']}")
        lineas.append(f"- Estado: {fila['estado']}")
        lineas.append(f"- Precio en la pagina: {fila.get('precio_pagina', '')}")
        lineas.append(f"- Titulo en la pagina: {fila.get('titulo_pagina', '')}")
        lineas.append(f"- Municipio/ubicacion: {fila.get('municipio', '')}")
        lineas.append(f"- Fecha pagina: {fila.get('fecha_pagina', '')}")
        lineas.append(f"- Montos en la descripcion: {fila.get('montos_en_descripcion', '') or 'ninguno'}")
        lineas.append(f"- Descripcion: {fila.get('descripcion', '') or 'sin descripcion'}")
        lineas.append("")
    salida_md = OUT_DIR / f"revision_descripciones_{marca}.md"
    salida_md.write_text("\n".join(lineas), encoding="utf-8")

    print()
    print(f"CSV: {salida_csv}")
    print(f"MD : {salida_md}")


if __name__ == "__main__":
    main()
