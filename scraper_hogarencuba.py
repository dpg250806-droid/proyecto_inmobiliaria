#!/usr/bin/env python3
"""Scraper reproducible para HogarEnCuba (La Habana).

El sitio es accesible publicamente y muestra fichas ricas (habitaciones,
banos, superficie, precio, actualizacion). Guarda listings sin sobrescribir
outputs existentes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from precio_moneda import extraer_precio_moneda, parsear_importe

BASE_URL = "https://hogarencuba.com"
START_URL = "https://hogarencuba.com/ventas/la-habana"


def fetch(url: str, timeout: int = 30) -> str:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    response.raise_for_status()
    body = response.text
    if any(marker in body[:2000].lower() for marker in ("cloudflare", "captcha", "verify you are human", "access denied")):
        raise RuntimeError(f"HogarEnCuba devolvio una pagina de bloqueo para {url}.")
    return body


def list_links(page_html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(page_html, "html.parser")
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not re.search(r"/HEC\d+(?:[-./?#]|$)", href, re.IGNORECASE) or not title or "cuarto" not in title.lower():
            continue
        full_url = urljoin(BASE_URL, href)
        if urlparse(full_url).netloc.lower() != urlparse(BASE_URL).netloc:
            continue
        if full_url not in seen:
            seen.add(full_url)
            result.append((full_url, title))
    return result


def detect_pages(page_html: str) -> int:
    soup = BeautifulSoup(page_html, "html.parser")
    page_numbers = [1]
    for anchor in soup.find_all("a", href=True):
        query = parse_qs(urlparse(anchor["href"]).query)
        for value in query.get("page", []):
            if value.isdigit():
                page_numbers.append(int(value))
    return max(page_numbers)


def number(text: str | None, pattern: str) -> float | None:
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    if not match:
        return None
    return parsear_importe(match.group(1))


def _walk_json_objects(value):
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(child for child in current.values() if isinstance(child, (dict, list)))
        elif isinstance(current, list):
            stack.extend(current)


def _jsonld_price_for_id(raw_html: str | None, property_id: str | None) -> tuple[float, str] | None:
    if not raw_html or not property_id:
        return None

    soup = BeautifulSoup(raw_html, "html.parser")
    matches = set()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            document = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        for item in _walk_json_objects(document):
            identifiers = {str(item.get(key, "")).strip() for key in ("sku", "identifier")}
            if property_id not in identifiers:
                continue
            offers = item.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers if isinstance(offers, list) else []:
                if not isinstance(offer, dict):
                    continue
                price = parsear_importe(str(offer.get("price", "")))
                currency = str(offer.get("priceCurrency", "")).strip().upper()
                if price is not None and price > 0 and currency in {"USD", "EUR", "CUC", "CUP"}:
                    matches.add((price, currency))

    return next(iter(matches)) if len(matches) == 1 else None


def _main_listing_text(detail_text: str) -> str:
    text = " ".join(detail_text.split())
    for marker in ("Propiedades similares", "Categorías relacionadas", "Related properties"):
        position = text.lower().find(marker.lower())
        if position >= 0:
            text = text[:position]
    return text


def _explicit_price_currency(text: str) -> str | None:
    match = re.search(r"\b(?:precio\s+en|price\s+in)\s+(USD|US\$|EUR|CUC|CUP)\b", text, re.IGNORECASE)
    if not match:
        return None
    currency = match.group(1).upper()
    return "USD" if currency == "US$" else currency


def _standalone_json_price(detail_text: str) -> float | None:
    try:
        document = json.loads(detail_text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(document, dict) or "price" not in document:
        return None
    price = parsear_importe(str(document["price"]))
    return price if price is not None and price > 0 else None


def parse_detail(detail_text: str, title: str, url: str, raw_html: str | None = None) -> dict:
    text = " ".join(detail_text.split())
    property_id = re.search(r"HEC\d+", title + " " + url)
    property_key = property_id.group(0) if property_id else None
    main_text = _main_listing_text(text)
    structured_price = _jsonld_price_for_id(raw_html, property_key)
    title_price, title_currency = extraer_precio_moneda(title)
    detail_price, detail_currency = extraer_precio_moneda(main_text)
    unlabelled_json_price = _standalone_json_price(detail_text)
    if structured_price:
        price_raw, moneda = structured_price
        price_method = "jsonld_identificador"
    elif unlabelled_json_price is not None:
        price_raw, moneda = unlabelled_json_price, None
        price_method = "json_sin_moneda"
    elif title_price is not None:
        price_raw, moneda = title_price, title_currency
        price_method = "titulo"
    elif detail_price is not None:
        price_raw, moneda = detail_price, detail_currency
        price_method = "texto_ficha"
    else:
        price_raw, moneda = None, None
        price_method = "no_identificado"

    explicit_currency = _explicit_price_currency(main_text)
    if explicit_currency and price_raw is not None:
        moneda = explicit_currency
        price_method += "+etiqueta_precio"
    price_evidence = (
        f"{price_method}; id={property_key or 'sin_id'}; precio={price_raw}; moneda={moneda or 'no_identificada'}"
    )
    slug_parts = [part for part in urlparse(url).path.split("/") if part]
    property_index = next(
        (index for index, part in enumerate(slug_parts) if re.search(r"HEC\d+", part, re.IGNORECASE)),
        len(slug_parts),
    )
    alcaldia_slug = slug_parts[property_index - 1] if property_index > 0 else None
    from urllib.parse import unquote
    if alcaldia_slug and alcaldia_slug.lower() not in {"ventas", "venta", "la-habana"}:
        ubicacion_raw = " ".join(unquote(alcaldia_slug).replace("-", " ").split()).title()
    else:
        ubicacion_raw = "La Habana"
    search_source = raw_html or detail_text
    bedrooms_match = re.search(r'"numberOfBedrooms"\s*:\s*(\d+)', search_source)
    habitaciones = float(bedrooms_match.group(1)) if bedrooms_match else number(
        text, r"(?:Cuartos?|habitaciones?)\s*:?\s*(\d[\d.,]*)"
    )
    if habitaciones is None:
        habitaciones = number(title, r"(\d[\d.,]*)\s*(?:cuartos?|habitaciones?)")
    bathroom_text_match = re.search(r"Ba.{1,8}os\s*:??\s*(\d[\d\.,]*)", text, flags=re.IGNORECASE)
    bathrooms_json_match = re.search(r'"numberOfFullBathrooms"\s*:\s*(\d+)', search_source)
    if bathroom_text_match:
        banos = float(bathroom_text_match.group(1))
    elif bathrooms_json_match and int(bathrooms_json_match.group(1)) > 0:
        banos = float(bathrooms_json_match.group(1))
    else:
        banos = None
    superficie = number(text, r"Superficie.*?(\d[\d.,]*)\s*m(?:2|²)")
    tipo = None
    tipo_match = re.search(r"(Casa|Apartamento|Penthouse|Villa|D[uú]plex)", title, flags=re.IGNORECASE)
    if tipo_match:
        tipo = tipo_match.group(1).lower()
    fecha_match = re.search(r"Actualizado:\s*hace\s+\d+\s+\w+", text)
    lower = (text + " " + detail_text).lower()
    features = {
        "garaje": 1 if "garaje" in lower else 0,
        "piscina": 1 if "piscina" in lower else 0,
        "terraza": 1 if "terraza" in lower else 0,
        "patio": 1 if "patio" in lower else 0,
        "balcon": 1 if re.search(r"balc[oó]n", lower) else 0,
        "jardin": 1 if re.search(r"jard[ií]n", lower) else 0,
    }
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
        "precio_metodo_extraccion": price_method,
        "precio_evidencia": price_evidence,
        "fecha_publicacion": (fecha_match.group(0).strip() if fecha_match else None),
        "canal": "plataforma_estructurada",
        "agencia_observada": "no verificado (plataforma individual)",
        "texto_evidencia": text[:400],
        **features,
    }


def _scrape_detail(index: int, detail_url: str, title: str, timeout: int, delay: float):
    try:
        detail_html = fetch(detail_url, timeout=timeout)
        detail_soup = BeautifulSoup(detail_html, "html.parser")
        detail_text = detail_soup.get_text(" ", strip=True)
        return index, parse_detail(detail_text, title, detail_url, detail_html), None
    except requests.RequestException as error:
        return index, None, error
    finally:
        if delay:
            time.sleep(delay)


def run(
    max_pages: int | None = None,
    delay: float = 0.5,
    output_dir: Path | None = None,
    workers: int = 3,
    timeout: int = 20,
) -> pd.DataFrame:
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages debe ser al menos 1.")
    if delay < 0:
        raise ValueError("delay no puede ser negativo.")
    if workers < 1 or workers > 5:
        raise ValueError("workers debe estar entre 1 y 5.")
    if timeout < 1:
        raise ValueError("timeout debe ser al menos 1 segundo.")
    collected: list[dict] = []
    failed_details = 0
    failed_urls: list[str] = []
    out_dir = output_dir or Path(__file__).resolve().parent / "outputs" / "hogarencuba"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"viviendas_hogarencuba_{stamp}.csv"
    first_page_html = fetch(START_URL, timeout=timeout)
    detected_pages = detect_pages(first_page_html)
    pages_to_process = min(detected_pages, max_pages) if max_pages else detected_pages
    print(f"Paginas detectadas: {detected_pages}; se procesaran: {pages_to_process}")
    detail_links: list[tuple[int, str, str]] = []
    for page in range(1, pages_to_process + 1):
        url = START_URL if page == 1 else f"{START_URL}?page={page}"
        page_html = first_page_html if page == 1 else fetch(url, timeout=timeout)
        links = list_links(page_html)
        print(f"Pagina {page}: {len(links)} fichas")
        if not links:
            raise RuntimeError(f"No se detectaron fichas en la pagina {page}; se cancela sin crear un CSV incompleto.")
        first_index = len(detail_links)
        detail_links.extend((first_index + idx, detail_url, title) for idx, (detail_url, title) in enumerate(links))
        if page < pages_to_process:
            time.sleep(delay)

    print(f"Fichas individuales a consultar: {len(detail_links)}; concurrencia: {workers}")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_scrape_detail, index, url, title, timeout, delay): (index, url, title)
            for index, url, title in detail_links
        }
        results = []
        for future in as_completed(futures):
            index, url, title = futures[future]
            result_index, record, error = future.result()
            if error:
                failed_details += 1
                failed_urls.append(url)
                print(f"  ERROR {url}: {error}")
            else:
                results.append((result_index, record))
                print(
                    f"  {len(results) + failed_details:03d}/{len(detail_links)} "
                    f"{record['id_local']} {record['habitaciones']} hab "
                    f"{record['banos']} ban {record['superficie_m2']} m2"
                )
        collected = [record for _, record in sorted(results, key=lambda item: item[0])]
    frame = pd.DataFrame(collected)
    if frame.empty:
        raise RuntimeError("No se recopilo ninguna ficha de HogarEnCuba; no se creo un CSV vacio.")
    frame["recoleccion_completa"] = not failed_details and pages_to_process == detected_pages
    frame["fichas_fallidas"] = failed_details
    frame["paginas_total_detectadas"] = detected_pages
    frame["paginas_procesadas"] = pages_to_process
    frame = frame.drop_duplicates(subset=["url"], keep="last").reset_index(drop=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8-sig", newline="") as handle:
        frame.to_csv(handle, index=False)
    print(f"\nGuardado: {path}")
    print(f"Fichas guardadas: {len(frame)}; fichas fallidas: {failed_details}")
    if failed_details:
        print("ADVERTENCIA: el snapshot es parcial; vuelve a revisar las fichas fallidas antes del analisis.")
        for failed_url in failed_urls:
            print(f"  Ficha pendiente: {failed_url}")
    print(frame.head().to_string(index=False)[:1500])
    return frame


def main():
    parser = argparse.ArgumentParser(description="Scraper HogarEnCuba (La Habana)")
    parser.add_argument("--max-pages", type=int, help="Limita las paginas de listado (por defecto detecta y procesa todas).")
    parser.add_argument("--delay", type=float, default=1.0, help="Espera entre requests (segundos)")
    parser.add_argument("--workers", type=int, default=3, help="Solicitudes simultaneas de fichas (1-5).")
    parser.add_argument("--timeout", type=int, default=20, help="Timeout por solicitud, en segundos.")
    args = parser.parse_args()
    run(max_pages=args.max_pages, delay=args.delay, workers=args.workers, timeout=args.timeout)


if __name__ == "__main__":
    main()