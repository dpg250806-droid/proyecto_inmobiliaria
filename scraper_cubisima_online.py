#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scraper online no destructivo para Cubisima (La Habana).

Guarda un CSV derivado en outputs/cubisima/. No modifica viviendas_cubisima.csv
ni otros archivos existentes.
"""

from __future__ import annotations

import datetime
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent
BASE_URL = "https://www.cubisima.com/casas/anuncios/la-habana/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def convertir_precio(texto):
    texto = texto.strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def extraer_datos_tarjeta(titulo, texto_tarjeta, url_anuncio=None):
    titulo_minuscula = titulo.lower()
    texto_minuscula = texto_tarjeta.lower()

    tipo = None
    for posible_tipo in ["apartamento", "casa", "penthouse", "habitacion", "prop horizontal"]:
        if titulo_minuscula.startswith(posible_tipo):
            tipo = posible_tipo
            break

    habitaciones = None
    encontrado = re.search(r"(\d+(?:[.,]5)?)\s+cuartos?", titulo_minuscula)
    if encontrado:
        habitaciones = float(encontrado.group(1).replace(",", "."))

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

    precio = None
    moneda = None
    encontrado_dolares = re.search(r"\$\s*([\d.,]+)", texto_tarjeta)
    if encontrado_dolares:
        numero = encontrado_dolares.group(1).replace(",", "")
        try:
            precio = float(numero)
            moneda = "USD"
        except ValueError:
            pass

    if precio is None:
        encontrado_euros = re.search(r"([\d.]+,\d{2})\s*â‚¬", texto_tarjeta)
        if encontrado_euros:
            precio = convertir_precio(encontrado_euros.group(1))
            moneda = "EUR"

    moneda_original = None
    if "cuc" in texto_minuscula:
        moneda_original = "CUC"
    elif "usd" in texto_minuscula:
        moneda_original = "USD"
    elif "eur" in texto_minuscula or "â‚¬" in texto_tarjeta:
        moneda_original = "EUR"

    encontrado_cuc_url = re.search(r"-(\d+)-cuc(?:-|[.!?]|$)", url_anuncio or "", re.IGNORECASE)
    if encontrado_cuc_url and precio == float(encontrado_cuc_url.group(1)):
        moneda = "CUC"
        moneda_original = "CUC"

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


def main() -> None:
    respuesta = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")

    texto_pagina = soup.get_text(" ", strip=True)
    encontrado = re.search(r"P[aá]gina\s+\d+\s+de\s+(\d+)", texto_pagina, re.IGNORECASE)
    total_paginas = int(encontrado.group(1)) if encontrado else 1
    print("Total de paginas Cubisima detectadas:", total_paginas)

    todos = []
    for numero in range(1, total_paginas + 1):
        url = BASE_URL if numero == 1 else f"{BASE_URL}?page={numero}"
        print(f"Leyendo pagina {numero} de {total_paginas}: {url}")
        respuesta = requests.get(url, headers=HEADERS, timeout=30)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.text, "html.parser")

        anuncios_pagina = 0
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

            datos = extraer_datos_tarjeta(titulo, texto_tarjeta, url_anuncio)
            todos.append({
                "fuente": "Cubisima",
                "titulo": titulo,
                **datos,
                "url": url_anuncio,
                "pagina_origen": numero,
                "texto_tarjeta": texto_tarjeta,
            })
            anuncios_pagina += 1

        print(f"  Anuncios encontrados: {anuncios_pagina}")
        time.sleep(1)

    tabla = pd.DataFrame(todos)
    if "url" in tabla.columns:
        tabla = tabla.drop_duplicates(subset=["url", "titulo"])

    salida_dir = RAIZ / "outputs" / "cubisima"
    salida_dir.mkdir(parents=True, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    salida = salida_dir / f"viviendas_cubisima_online_{sello}.csv"
    tabla.to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"\nArchivo guardado: {salida}")
    print(f"Anuncios unicos: {len(tabla)}")


if __name__ == "__main__":
    main()
