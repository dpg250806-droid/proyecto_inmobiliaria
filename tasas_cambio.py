#!/usr/bin/env python3
"""Obtiene o registra tasas de cambio USD/EUR/CUC -> CUP (informal/formal).

Los sitios de ElToque usan proteccion anti-bot; si el acceso automatico falla,
el script no fabrica valores. Se puede pasar un HTML guardado o registrar valores
manuales. Siempre genera una fila auditable con estado y fecha.
"""
from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
import re

import requests

try:
    from curl_cffi import requests as curl_requests
except Exception:  # pragma: no cover
    curl_requests = None

REPO_ROOT = Path(__file__).resolve().parent
OUT_DIR = REPO_ROOT / "data" / "tasas"
URL = "https://eltoque.com/tasas-de-cambio-cuba"


def safe_request(url: str, timeout: int = 20):
    attempts = []
    # 1) requests
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        attempts.append({"method": "requests", "status": r.status_code, "ok": r.ok, "error": ""})
        if r.ok:
            return r.text, attempts
    except Exception as exc:
        attempts.append({"method": "requests", "status": None, "ok": False, "error": str(exc)})

    # 2) curl_cffi (si esta disponible)
    if curl_requests is not None:
        try:
            r = curl_requests.get(url, impersonate="chrome131", timeout=timeout)
            attempts.append({"method": "curl_cffi", "status": r.status_code, "ok": r.status_code == 200, "error": ""})
            if r.status_code == 200:
                return r.text, attempts
        except Exception as exc:
            attempts.append({"method": "curl_cffi", "status": None, "ok": False, "error": str(exc)})

    return None, attempts


def compact(text: str | None):
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip()


def find_number(text: str | None, label: str, radius: int = 140):
    """Busca un numero decimal cerca de una etiqueta de texto."""
    if not text:
        return None
    text = compact(text)
    # Normalizar espacios.
    escaped = re.escape(label)
    pattern = rf"{escaped}.{{0,{radius}}}?(\d[\d.,]{{1,12}})"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1)
    candidate = raw.replace(" ", "")
    if "," in candidate and "." in candidate:
        candidate = candidate.replace(".", "").replace(",", ".")
    elif "," in candidate:
        candidate = candidate.replace(",", ".")
    try:
        return float(candidate)
    except ValueError:
        return None


def parse_page(text: str | None):
    parsed = {
        "usd_informal": None,
        "eur_informal": None,
        "usd_formal_buy": None,
        "usd_formal_sell": None,
        "eur_formal_buy": None,
        "eur_formal_sell": None,
        "observaciones": "",
    }
    if not text:
        parsed["observaciones"] = "No se pudo leer la pagina."
        return parsed

    # La pagina organiza el mercado informal y el formal en el mismo documento.
    low = text.lower()
    informal_pos = low.find("mercado informal")
    formal_pos = low.find("mercado formal")
    informal_text = compact(text[informal_pos:formal_pos]) if formal_pos > informal_pos else compact(text)
    formal_text = compact(text[formal_pos:]) if formal_pos >= 0 else None

    parsed["usd_informal"] = find_number(informal_text, "1 USD")
    parsed["eur_informal"] = find_number(informal_text, "1 EUR")
    parsed["usd_formal_buy"] = find_number(formal_text, "usd")
    parsed["eur_formal_buy"] = find_number(formal_text, "eur")
    # Valores complejos de la tabla formal varian por banco y presentacion; se documentan
    # por separado mediante CUP/USD para no inferir una tabla incorrecta.
    parsed["observaciones"] = (
        "Parseo heuristico de ElToque. Verificar visualmente la tabla formal antes de usarla en conversiones."
    )
    return parsed


def write_csv(record: dict):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUT_DIR / f"tasas_cambio_{stamp}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(record.keys()))
        writer.writeheader()
        writer.writerow(record)
    return path


def main():
    parser = argparse.ArgumentParser(description="Registrar tasas USD/EUR -> CUP informal/formal")
    parser.add_argument("--html", help="Ruta a un HTML guardado de ElToque.")
    parser.add_argument("--no-network", action="store_true", help="No intentar acceso automatico.")
    parser.add_argument("--url", default=URL, help="URL de consulta.")
    parser.add_argument("--usd-informal", type=float, help="Valor manual informal USD->CUP.")
    parser.add_argument("--eur-informal", type=float, help="Valor manual informal EUR->CUP.")
    parser.add_argument("--usd-formal", type=float, help="Valor manual formal USD->CUP.")
    parser.add_argument("--eur-formal", type=float, help="Valor manual formal EUR->CUP.")
    parser.add_argument("--cuc-informal", type=float, help="Tasa manual verificada informal CUC->CUP.")
    parser.add_argument("--cuc-formal", type=float, help="Tasa manual verificada formal CUC->CUP.")
    parser.add_argument("--fuente-cuc", help="Fuente independiente que respalda la tasa CUC/CUP manual.")
    parser.add_argument("--fuente", default="ElToque", help="Fuente registrada.")
    args = parser.parse_args()
    for name in ("cuc_informal", "cuc_formal"):
        value = getattr(args, name)
        if value is not None and value <= 0:
            parser.error(f"--{name.replace('_', '-')} debe ser mayor que cero.")
    if any(value is not None for value in (args.cuc_informal, args.cuc_formal)) and not args.fuente_cuc:
        parser.error("Indica --fuente-cuc cuando registres una tasa CUC/CUP.")

    body = None
    attempts = []
    if args.html:
        body = Path(args.html).read_text(encoding="utf-8", errors="replace")
        attempts.append({"method": "html_local", "status": 200, "ok": True, "error": ""})
    elif not args.no_network:
        body, attempts = safe_request(args.url)

    parsed = parse_page(body) if body else {}
    record = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": args.fuente,
        "url": args.url if not args.html else str(Path(args.html)),
        "estado_acceso": ("ok" if body else ("registro_manual" if any(v is not None for v in [args.usd_informal, args.eur_informal, args.usd_formal, args.eur_formal, args.cuc_informal, args.cuc_formal]) else "bloqueado_o_no_disponible")),
        "usd_informal_cup": args.usd_informal if args.usd_informal is not None else parsed.get("usd_informal"),
        "eur_informal_cup": args.eur_informal if args.eur_informal is not None else parsed.get("eur_informal"),
        "usd_formal_cup": args.usd_formal if args.usd_formal is not None else parsed.get("usd_formal_buy"),
        "eur_formal_cup": args.eur_formal if args.eur_formal is not None else parsed.get("eur_formal_buy"),
        "cuc_informal_cup": args.cuc_informal,
        "cuc_formal_cup": args.cuc_formal,
        "fuente_cuc": args.fuente_cuc,
        "metodo_acceso": ", ".join(a["method"] for a in attempts) if attempts else "manual",
        "intentos": str(attempts).replace("\"", "'"),
        "observacion": (
            "Si los valores automaticos salieron vacios, registrar tasas manuales verificadas o cargar HTML local. "
            "CUC no se consulta automaticamente; sus campos solo se registran con una tasa manual verificada. "
            "Las tasas formal/informal deben usarse solo para conversion documental."
        ),
    }

    path = write_csv(record)
    print(f"Archivo de tasas: {path}")
    print(record)
    if record["estado_acceso"] != "ok" or record["usd_informal_cup"] is None:
        print("\nADVERTENCIA: el acceso automatico fue bloqueado. Usa --html o los flags manuales.")


if __name__ == "__main__":
    main()
