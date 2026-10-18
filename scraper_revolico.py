#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scraper hibrido y automatizado de Revolico.

Motores disponibles:
- playwright: navegador Chromium automatizado (mejor opcion para evitar 403).
- requests: HTTP directo (sujeto a bloqueo anti-bot).
- local: procesa las paginas HTML guardadas manualmente.

El archivo de salida por defecto no sobrescribe enlaces_anuncios_revolico.csv.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent
PAGINAS_LOCALES = RAIZ / "paginas_revolico"
CACHE_ONLINE = RAIZ / "paginas_revolico_online"
SALIDA_POR_DEFECTO = RAIZ / "enlaces_anuncios_revolico_reparado.csv"

URL_BASE = "https://www.revolico.com/search?category=inmobiliaria&subcategory=inmobiliaria-casas&province=la-habana"


class SitioBloqueadoError(RuntimeError):
    pass


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


def url_pagina(numero: int) -> str:
    if numero <= 1:
        return URL_BASE
    return f"{URL_BASE}&page={numero}"


def descargar_requests(url: str, intentos: int = 3, espera: float = 2.0) -> str:
    session = requests.Session()
    ultimo_error = None

    for intento in range(1, intentos + 1):
        try:
            respuesta = session.get(url, headers=encabezados_navegador(), timeout=30)
            cuerpo = respuesta.text[:800].lower()
            if respuesta.status_code in (401, 403):
                if "just a moment" in cuerpo or "cloudflare" in cuerpo or "challenge" in cuerpo:
                    raise SitioBloqueadoError(
                        "Revolico bloqueo la peticion automatica (HTTP "
                        f"{respuesta.status_code}, proteccion anti-bot/Cloudflare)."
                    )
                raise SitioBloqueadoError(f"Revolico respondio HTTP {respuesta.status_code} para {url}.")
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


def descargar_playwright(url: str, timeout_ms: int = 60000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright no esta instalado. Ejecute: python -m pip install playwright && python -m playwright install chromium"
        ) from exc

    with sync_playwright() as playwright:
        # Si el binario de Playwright no esta instalado, se usa Chrome del sistema.
        try:
            navegador = playwright.chromium.launch(headless=True)
        except Exception:
            navegador = playwright.chromium.launch(channel="chrome", headless=True)

        contexto = navegador.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
        )
        pagina = contexto.new_page()
        pagina.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        try:
            pagina.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            pagina.wait_for_selector('a[href*="/item/"]', timeout=timeout_ms)
            # Pequeña espera adicional para que termine la hidratacion de Next.js.
            pagina.wait_for_timeout(3000)
            html = pagina.content()
        finally:
            contexto.close()
            navegador.close()

    cuerpo = html[:1000].lower()
    if "just a moment" in cuerpo or "cloudflare" in cuerpo or "verify you are human" in cuerpo:
        raise SitioBloqueadoError("Playwright recibio una pagina de bloqueo de Cloudflare o challenge.")
    return html


def encontrar_contenedor_individual(enlace):
    elemento = enlace
    for _ in range(10):
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
            }
        )

    return resultado


def leer_pagina_local(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8", errors="ignore")


def guardar_cache(origen: str, html: str, guardar: bool) -> None:
    if not guardar:
        return
    CACHE_ONLINE.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ruta = CACHE_ONLINE / f"{Path(origen).stem}_{sello}{Path(origen).suffix}"
    with ruta.open("x", encoding="utf-8") as handle:
        handle.write(html)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de Revolico para inmobiliaria en La Habana.")
    parser.add_argument("--motor", choices=["auto", "playwright", "requests", "local"], default="auto")
    parser.add_argument("--max-paginas", type=int, default=8)
    parser.add_argument("--salida", type=Path, help="Destino nuevo; si no se indica se crea un archivo fechado.")
    parser.add_argument("--espera", type=float, default=2.0)
    parser.add_argument("--no-guardar-html", action="store_true")
    args = parser.parse_args()

    todos: list[dict] = []
    estado_online = "no intentado"

    paginas_solicitadas = max(1, args.max_paginas)

    if args.motor in ("auto", "playwright"):
        try:
            for numero in range(1, paginas_solicitadas + 1):
                url = url_pagina(numero)
                print(f"Descargando online con Playwright: {url}")
                html = descargar_playwright(url)
                origen = f"revolico_online_pagina_{numero}.html"
                guardar_cache(origen, html, not args.no_guardar_html)
                anuncios = extraer_anuncios(html, origen)
                todos.extend(anuncios)
                print(f"  Anuncios encontrados: {len(anuncios)}")
                if not anuncios:
                    break
                time.sleep(args.espera)
            estado_online = "playwright OK"
        except Exception as exc:
            estado_online = f"playwright fallo: {exc}"
            print("Playwright no disponible o bloqueado:", ascii(exc))
            if args.motor == "playwright":
                raise

    if args.motor in ("auto", "requests") and not todos:
        try:
            for numero in range(1, paginas_solicitadas + 1):
                url = url_pagina(numero)
                print(f"Descargando online con requests: {url}")
                html = descargar_requests(url)
                origen = f"revolico_requests_pagina_{numero}.html"
                guardar_cache(origen, html, not args.no_guardar_html)
                anuncios = extraer_anuncios(html, origen)
                todos.extend(anuncios)
                print(f"  Anuncios encontrados: {len(anuncios)}")
                if not anuncios:
                    break
                time.sleep(args.espera)
            estado_online = "requests OK"
        except Exception as exc:
            estado_online = f"requests fallo: {exc}"
            print("Requests no pudo obtener la pagina:", ascii(exc))
            if args.motor == "requests":
                raise

    usar_local = args.motor == "local" or not todos
    if usar_local:
        archivos = sorted(PAGINAS_LOCALES.glob("*.html")) + sorted(PAGINAS_LOCALES.glob("*.htm"))
        archivos = sorted(set(archivos))
        if not archivos:
            raise FileNotFoundError("No hay paginas locales y la descarga online no fue posible.")
        limite = min(paginas_solicitadas, len(archivos))
        for ruta in archivos[:limite]:
            print(f"Leyendo localmente: {ruta.name}")
            html = leer_pagina_local(ruta)
            anuncios = extraer_anuncios(html, ruta.name)
            todos.extend(anuncios)
            print(f"  Anuncios encontrados: {len(anuncios)}")

    vistos: set[str] = set()
    unicos: list[dict] = []
    for anuncio in todos:
        if anuncio["url"] in vistos:
            continue
        vistos.add(anuncio["url"])
        unicos.append(anuncio)

    tabla = pd.DataFrame(unicos)
    if tabla.empty:
        raise RuntimeError("No se extrajeron anuncios. Revise el bloqueo online o las paginas locales.")

    salida = args.salida or SALIDA_POR_DEFECTO.with_name(
        f"{SALIDA_POR_DEFECTO.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{SALIDA_POR_DEFECTO.suffix}"
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("x", encoding="utf-8-sig", newline="") as handle:
        tabla.to_csv(handle, index=False)

    print("\n--- RESULTADO ---")
    print(f"Estado online: {estado_online}")
    print(f"Anuncios antes de quitar duplicados: {len(todos)}")
    print(f"Anuncios unicos guardados: {len(tabla)}")
    print(f"Archivo guardado: {salida}")


if __name__ == "__main__":
    main()
