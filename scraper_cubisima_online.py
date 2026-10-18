#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scraper online no destructivo para Cubisima (La Habana).

Guarda un CSV derivado en outputs/cubisima/. No modifica viviendas_cubisima.csv
ni otros archivos existentes.
"""

from __future__ import annotations

import datetime
import argparse
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from precio_moneda import extraer_precio_moneda, parsear_importe

RAIZ = Path(__file__).resolve().parent
BASE_URL = "https://www.cubisima.com/casas/anuncios/la-habana/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = RAIZ / "outputs" / "cubisima"


def convertir_precio(texto):
    return parsear_importe(texto)


def extraer_datos_tarjeta(titulo, texto_tarjeta, url_anuncio=None):
    titulo_minuscula = titulo.lower()
    texto_minuscula = texto_tarjeta.lower()

    tipo = None
    for posible_tipo in ["apartamento", "casa", "penthouse", "habitacion", "prop horizontal"]:
        if titulo_minuscula.startswith(posible_tipo):
            tipo = posible_tipo
            break

    habitaciones = None
    encontrado = re.search(r"(\d+)(?:([.,]5)|(½))?\s+cuartos?", titulo_minuscula)
    if encontrado:
        habitaciones = float(encontrado.group(1))
        if encontrado.group(2):
            habitaciones += 0.5
        elif encontrado.group(3):
            habitaciones += 0.5

    banos = None
    encontrado = re.search(r"(\d+)\s+baños?", texto_minuscula)
    if encontrado:
        banos = int(encontrado.group(1))

    zona = None
    if " en " in titulo_minuscula:
        zona = titulo.split(" en ", 1)[-1].strip().title()

    fecha = None
    encontrado = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", texto_tarjeta)
    if encontrado:
        fecha = encontrado.group(0)

    precio, moneda = extraer_precio_moneda(texto_tarjeta, url_anuncio)
    moneda_original = moneda

    garaje = "si" if "garaje" in texto_minuscula else "no"
    piscina = "si" if "piscina" in texto_minuscula else "no"
    terraza = "si" if "terraza" in texto_minuscula else "no"
    patio = "si" if "patio" in texto_minuscula else "no"
    balcon = "si" if "balcon" in texto_minuscula else "no"
    jardin = "si" if "jardin" in texto_minuscula else "no"

    return {
        "tipo": tipo,
        "zona": zona,
        "habitaciones": habitaciones,
        "banos": banos,
        "precio": precio,
        "moneda": moneda,
        "moneda_original": moneda_original,
        "fecha": fecha,
        "garaje": garaje,
        "piscina": piscina,
        "terraza": terraza,
        "patio": patio,
        "balcon": balcon,
        "jardin": jardin,
    }


def validar_respuesta(respuesta, url: str) -> str:
    respuesta.raise_for_status()
    texto = respuesta.text
    if respuesta.status_code != 200:
        raise RuntimeError(f"Cubisima respondio HTTP {respuesta.status_code} para {url}.")
    cuerpo = texto[:2000].lower()
    if any(marca in cuerpo for marca in ("cloudflare", "captcha", "verify you are human", "access denied")):
        raise RuntimeError(f"Cubisima devolvio una pagina de bloqueo para {url}.")
    return texto


def detectar_paginas(texto_pagina: str) -> int:
    encontrado = re.search(r"\bP.{0,2}gina\s+\d+\s+de\s+(\d+)", texto_pagina, re.IGNORECASE)
    return int(encontrado.group(1)) if encontrado else 1


def extraer_anuncios_pagina(html: str, numero: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    anuncios = []
    for encabezado in soup.find_all(["h3", "h4"]):
        titulo = encabezado.get_text(" ", strip=True)
        if "cuarto" not in titulo.lower():
            continue

        contenedor = encabezado
        for _ in range(6):
            padre = contenedor.parent
            if padre is None:
                break
            texto_padre = padre.get_text(" ", strip=True)
            titulos_dentro = [
                h for h in padre.find_all(["h3", "h4"])
                if "cuarto" in h.get_text(" ", strip=True).lower()
            ]
            if re.search(r"ver m[aá]s", texto_padre.lower()) and len(titulos_dentro) == 1:
                contenedor = padre
                break
            contenedor = padre

        texto_tarjeta = contenedor.get_text(" ", strip=True)
        url_anuncio = None
        for enlace in contenedor.find_all("a", href=True):
            if re.search(r"ver m[aá]s", enlace.get_text(" ", strip=True).lower()):
                url_anuncio = urljoin(BASE_URL, enlace.get("href"))
                break

        anuncios.append({
            "fuente": "Cubisima",
            "titulo": titulo,
            **extraer_datos_tarjeta(titulo, texto_tarjeta, url_anuncio),
            "url": url_anuncio,
            "pagina_origen": numero,
            "texto_tarjeta": texto_tarjeta,
        })
    return anuncios


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Scraper online no destructivo para Cubisima.")
    parser.add_argument("--max-pages", type=int, help="Limita las paginas procesadas.")
    parser.add_argument("--delay", type=float, default=1.0, help="Espera entre solicitudes.")
    parser.add_argument("--output", type=Path, help="Ruta de salida nueva; no puede existir.")
    args = parser.parse_args(argv)
    if args.max_pages is not None and args.max_pages < 1:
        parser.error("--max-pages debe ser al menos 1.")
    if args.delay < 0:
        parser.error("--delay no puede ser negativo.")

    respuesta = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    html_primera = validar_respuesta(respuesta, BASE_URL)
    soup = BeautifulSoup(respuesta.text, "html.parser")

    texto_pagina = soup.get_text(" ", strip=True)
    total_detectado = detectar_paginas(texto_pagina)
    total_paginas = min(total_detectado, args.max_pages) if args.max_pages else total_detectado
    if total_detectado == 1:
        print("Aviso: no se detecto el total de paginas; se procesara solo la primera.")
    print("Total de paginas Cubisima detectadas:", total_paginas)

    todos = []
    for numero in range(1, total_paginas + 1):
        url = BASE_URL if numero == 1 else f"{BASE_URL}?page={numero}"
        print(f"Leyendo pagina {numero} de {total_paginas}: {url}")
        html = html_primera if numero == 1 else validar_respuesta(
            requests.get(url, headers=HEADERS, timeout=30), url
        )
        anuncios_pagina = extraer_anuncios_pagina(html, numero)
        if not anuncios_pagina:
            raise RuntimeError(
                f"No se detectaron anuncios en la pagina {numero}; "
                "se aborta para evitar guardar una captura vacia o incompleta."
            )
        todos.extend(anuncios_pagina)
        print(f"  Anuncios encontrados: {len(anuncios_pagina)}")
        if numero < total_paginas:
            time.sleep(args.delay)

    tabla = pd.DataFrame(todos)
    if "url" in tabla.columns:
        tabla = tabla.drop_duplicates(subset=["url", "titulo"])
    if tabla.empty:
        raise RuntimeError("No se extrajeron anuncios de Cubisima.")
    tabla["paginas_total_detectadas"] = total_detectado
    tabla["paginas_procesadas"] = total_paginas

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    salida = args.output or OUTPUT_DIR / f"viviendas_cubisima_online_{sello}.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("x", encoding="utf-8-sig", newline="") as handle:
        tabla.to_csv(handle, index=False)
    print(f"\nArchivo guardado: {salida}")
    print(f"Anuncios unicos: {len(tabla)}")


if __name__ == "__main__":
    main()
