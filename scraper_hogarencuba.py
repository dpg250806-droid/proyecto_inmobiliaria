#!/usr/bin/env python3
"""Scraper reproducible para HogarEnCuba (La Habana).

El sitio es accesible publicamente y muestra fichas ricas (habitaciones,
banos, superficie, precio, actualizacion). Guarda listings sin sobrescribir
outputs existentes.
"""
from __future__ import annotations

import argparse
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://hogarencuba.com"
START_URL = "https://hogarencuba.com/ventas/la-habana"


def fetch(url: str, timeout: int = 30) -> str:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    response.raise_for_status()
    return response.text


def list_links(page_html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(page_html, "html.parser")
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not re.search(r"/HEC\d+", href) or not title or "cuarto" not in title.lower():
            continue
        if href not in seen:
            seen.add(href)
            result.append((BASE_URL + href if href.startswith("/") else href, title))
    return result


def number(text: str | None, pattern: str) -> float | None:
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_detail(detail_text: str, title: str, url: str) -> dict:
    text = " ".join(detail_text.split())
    property_id = re.search(r"HEC\d+", title + " " + url)
    price_match = re.search(r"(?:por \$|por US\$)\s*([\d\.,]+)", title + " " + text)
    price_raw = None
    if price_match:
        raw = price_match.group(1)
        price_raw = float(raw.replace(".", "").replace(",", "."))
    moneda = "USD"
    if re.search(r"(EUR|â‚¬)", title + " " + text, flags=re.IGNORECASE):
        moneda = "EUR"
    slug_parts = [p for p in url.split("/") if p]
    alcaldia_slug = slug_parts[-2] if len(slug_parts) >= 2 else None
    from urllib.parse import unquote
    if alcaldia_slug and not alcaldia_slug.lower().startswith("la-habana"):
        ubicacion_raw = " ".join(unquote(alcaldia_slug).replace("-", " ").split()).title()
    else:
        ubicacion_raw = "La Habana"
    superficie = number(text, r"Superficie.*?(\d[\d\.,]*)\s*m(?:2|Â²)")
    habitaciones = number(text, r"(?:Cuartos?|habitaciones?)\s*:?\s*(\d[\d\.,]*)")
    banos = number(text, r"(?:Ba.os|Banos)\s*:??\s*(\d[\d\.,]*)")
    tipo = None
    tipo_match = re.search(r"(Casa|Apartamento|Penthouse|Villa|Duplex|DÃºplex)", title, flags=re.IGNORECASE)
    if tipo_match:
        tipo = tipo_match.group(1).lower().replace("Ã¡", "a").replace("Ãº", "u")
    fecha_match = re.search(r"Actualizado:\s*hace[^.]*", text)
    return {
        "fuente": "HogarEnCuba",
        "id_local": property_id.group(0) if property_id else None,
        "titulo": title,
        "url": url,
        "tipo_vivienda": tipo,
        "ubicacion_raw": ubicacion_raw,
        "habitaciones": habitaciones,
        "banos": banos,
        "superficie_m2": superficie,
        "precio_original": price_raw,
        "moneda": moneda,
        "fecha_publicacion": (fecha_match.group(0).strip() if fecha_match else None),
        "canal": "plataforma_estructurada",
        "agencia_observada": "no verificado (plataforma individual)",
        "texto_evidencia": text[:400],
    }


def run(max_pages: int = 1, delay: float = 1.0) -> pd.DataFrame:
    collected: list[dict] = []
    for page in range(1, max_pages + 1):
        url = START_URL if page == 1 else f"{START_URL}?page={page}"
        links = list_links(fetch(url))
        print(f"Pagina {page}: {len(links)} fichas")
        for idx, (detail_url, title) in enumerate(links, start=1):
            try:
                detail_html = fetch(detail_url)
                detail_soup = BeautifulSoup(detail_html, "html.parser")
                detail_text = detail_soup.get_text(" ", strip=True)
                record = parse_detail(detail_text, title, detail_url)
                collected.append(record)
                print(f"  {idx:03d}/{len(links)} {record['id_local']} {record['habitaciones']} hab {record['banos']} ban {record['superficie_m2']} m2")
                time.sleep(delay)
            except Exception as error:
                print(f"  ERROR {detail_url}: {error}")
        time.sleep(delay)
    frame = pd.DataFrame(collected)
    out_dir = Path(__file__).resolve().parent / "outputs" / "hogarencuba"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"viviendas_hogarencuba_{stamp}.csv"
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {path}")
    print(frame.head().to_string(index=False)[:1500])
    return frame


def main():
    parser = argparse.ArgumentParser(description="Scraper HogarEnCuba (La Habana)")
    parser.add_argument("--max-pages", type=int, default=1, help="Cantidad de paginas de listado")
    parser.add_argument("--delay", type=float, default=1.0, help="Espera entre requests (segundos)")
    args = parser.parse_args()
    run(max_pages=args.max_pages, delay=args.delay)


if __name__ == "__main__":
    main()