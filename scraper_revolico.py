#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scraper hibrido de Revolico para el proyecto inmobiliario.

Intenta descargar directamente las paginas online de Revolico. Si el sitio bloquea
la peticion con HTTP 403/401 (Cloudflare u otra proteccion), puede usar como
respaldo las paginas HTML guardadas manualmente en paginas_revolico/.

El archivo de salida por defecto no sobrescribe enlaces_anuncios_revolico.csv.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


RAIZ = Path(__file__).resolve().parent
PAGINAS_LOCALES = RAIZ / "paginas_revolico"
SALIDA_POR_DEFECTO = RAIZ / "enlaces_anuncios_revolico_reparado.csv"

URL_BASE = "https://www.revolico.com/search?category=inmobiliaria&subcategory=inmobiliaria-casas&province=la-habana"


def encabezados_navegador() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }


class SitioBloqueadoError(RuntimeError):
    """Se lanza cuando Revolico responde con una pagina de bloqueo o challenge."""


def descargar_online(url: str, intentos: int = 3, espera: float = 2.0) -> str:
    session = requests.Session()
    ultimo_error: Exception | None = None

    for intento in range(1, intentos + 1):
        try:
            respuesta = session.get(url, headers=encabezados_navegador(), timeout=30)
            if respuesta.status_code in (401, 403):
                cuerpo = respuesta.text[:500].lower()
                if "just a moment" in cuerpo or "cloudflare" in cuerpo or "challenge" in cuerpo:
                    raise SitioBloqueadoError(
                        "Revolico bloqueo la peticion automatica (HTTP "
                        f"{respuesta.status_code}, proteccion anti-bot/Cloudflare)."
                    )
                raise SitioBloqueadoError(
                    f"Revolico respondio HTTP {respuesta.status_code} para {url}."
                )
            if respuesta.status_code != 200:
                raise RuntimeError(f"HTTP {respuesta.status_code} al solicitar {url}.")
            return respuesta.text
        except SitioBloqueadoError:
            raise
        except requests.RequestException as exc:
            ultimo_error = exc
            if intento < intentos:
                time.sleep(espera * intento)
            else:
                raise RuntimeError(f"No fue posible descargar {url}: {exc}") from exc

    raise RuntimeError(f"Error inesperado al descargar {url}: {ultimo_error}")


def encontrar_contenedor_individual(enlace):
    """Devuelve el ancestro mas cercano que contiene solo este anuncio.

    La extraccion anterior tomaba un ancestro compartido, lo que mezclaba
    varios anuncios en texto_tarjeta. Esta version evita esa contaminacion.
    """

    elemento = enlace
    for _ in range(8):
        elemento = elemento.parent
        if elemento is None:
            break
        enlaces_item = [
            a for a in elemento.find_all("a", href=True)
            if "/item/" in a.get("href", "") and "/item/publish" not in a.get("href", "")
        ]
        if len(enlaces_item) == 1:
            return elemento
    return enlace


def extraer_anuncios(html: str, origen: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    resultado: list[dict] = []
    vistos: set[str] = set()

    for enlace in soup.find_all("a", href=True):
        href = enlace.get("href", "")
        if "/item/" not in href or "/item/publish" in href:
            continue

        titulo = enlace.get_text(" ", strip=True)
        if not titulo:
            continue

        url = urljoin("https://www.revolico.com", href)
        if url in vistos:
            continue
        vistos.add(url)

        contenedor = encontrar_contenedor_individual(enlace)
        resultado.append(
            {
                "titulo": titulo,
                "texto_tarjeta": contenedor.get_text(" ", strip=True),
                "url": url,
                "pagina_origen": origen,
                "nivel_contenedor": None,
            }
        )

    return resultado


def leer_pagina_local(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8", errors="ignore")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper hibrido de Revolico para inmobiliaria en La Habana.")
    parser.add_argument("--fuente", choices=["auto", "online", "local"], default="auto")
    parser.add_argument("--max-paginas", type=int, default=8)
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument("--espera", type=float, default=2.0)
    args = parser.parse_args()

    todos: list[dict] = []
    estado_online = "no intentado"

    if args.fuente in ("auto", "online"):
        try:
            # En esta version solo se prueba la primera URL. El resto de paginas
            # puede añadirse cuando la API o la paginacion estable esten disponibles.
            html = descargar_online(URL_BASE)
            estado_online = "OK"
            anuncios = extraer_anuncios(html, "revolico_online_pagina_1.html")
            todos.extend(anuncios)
            print("Descarga online: OK")
            print(f"Anuncios encontrados online: {len(anuncios)}")
        except SitioBloqueadoError as exc:
            estado_online = f"bloqueado: {exc}"
            print(f"Descarga online bloqueada: {exc}")
            if args.fuente == "online":
                raise
        except Exception as exc:
            estado_online = f"error: {exc}"
            print(f"Error online: {exc}")
            if args.fuente == "online":
                raise

    usar_local = args.fuente == "local" or (args.fuente == "auto" and not todos)
    if usar_local:
        archivos = sorted(PAGINAS_LOCALES.glob("*.html")) + sorted(PAGINAS_LOCALES.glob("*.htm"))
        archivos = sorted(set(archivos))
        if not archivos:
            raise FileNotFoundError(
                "No hay paginas HTML locales en paginas_revolico/ y la descarga online no fue posible."
            )
        limite = min(args.max_paginas, len(archivos))
        for ruta in archivos[:limite]:
            print(f"Leyendo localmente: {ruta.name}")
            html = leer_pagina_local(ruta)
            anuncios = extraer_anuncios(html, ruta.name)
            todos.extend(anuncios)
            print(f"  Anuncios encontrados: {len(anuncios)}")
            time.sleep(0.2)

    # Eliminamos duplicados por URL preservando la primera aparicion.
    vistos: set[str] = set()
    unicos: list[dict] = []
    for anuncio in todos:
        if anuncio["url"] in vistos:
            continue
        vistos.add(anuncio["url"])
        unicos.append(anuncio)

    tabla = pd.DataFrame(unicos)

    # Quitamos el marcador auxiliar; el nivel real depende del ancestro, no de
    # un numero fijo.
    if "nivel_contenedor" in tabla.columns:
        tabla = tabla.drop(columns=["nivel_contenedor"])

    if tabla.empty:
        raise RuntimeError("No se extrajeron anuncios. Revise el bloqueo online o las paginas locales.")

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(args.salida, index=False, encoding="utf-8-sig")

    print("\n--- RESULTADO ---")
    print(f"Fuente online: {estado_online}")
    print(f"Anuncios antes de quitar duplicados: {len(todos)}")
    print(f"Anuncios unicos guardados: {len(tabla)}")
    print(f"Archivo guardado: {args.salida}")


if __name__ == "__main__":
    main()
