#!/usr/bin/env python3
"""Extrae habitaciones y banos del texto de cada anuncio de Revolico.

La tarjeta del listado solo aporta el titulo, y el titulo casi nunca menciona
banos. La pagina del anuncio si trae la descripcion completa, y el enlace
conserva el slug. Este script busca en esos tres textos (descripcion, titulo y
slug) la cantidad escrita por el anunciante, con patrones conservadores:

- digitos: "3 cuartos", "2 habitaciones", "1 dormitorio", "4 hab", "2 banos";
- palabras: "un cuarto", "dos banos", ... hasta diez;
- notacion habanera: "apto 2/4" cuenta 2 dormitorios (el segundo numero es el
  total de cuartos del apartamento y no se usa);
- banos con fraccion: "medio bano" y "2 banos y medio" suman 0.5.

Reglas: se toma la primera aparicion explicita; si el mismo texto menciona dos
cantidades distintas se conservan ambas en la evidencia y el conflicto queda
marcado; si no hay mencion no se rellena ningun valor (no se imputa). La fuente
queda registrada en las columnas `*_descripcion`, `*_titulo` y `*_slug`.

Tambien fija, para cada anuncio, la ventana de disponibilidad con evidencia:
el listado guardado (`paginas_revolico/`) donde el anuncio aparecia se descargo
el dia que marca el timestamp de Cloudflare incrustado en el HTML, y la pagina
del anuncio se consulto en `fecha_extraccion`; para los anuncios borrados o
despublicados la desaparicion ocurrio dentro de ese intervalo.

Salida: `outputs/metadatos_revolico/detalle_anuncios_revolico_<marca>.csv`.
`integrar_fuentes.py` la aplica con `aplicar_detalle_anuncios()`.

No consulta la redes: usa las descripciones ya descargadas. No modifica el
maestro ni los CSV originales.
"""
from __future__ import annotations

import argparse
import base64
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
META_DIR = ROOT / "outputs" / "metadatos_revolico"
PAGINAS_DIR = ROOT / "paginas_revolico"
OUT_DIR = META_DIR

NUMEROS = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}
TERMINOS_HABITACION = r"(?:cuartos?\b|habitaciones?\b|dormitorios?\b|hab\b)"
TERMINOS_BANO = r"(?:banos?\b|ban\b)"

PATRONES_HABITACION = [
    (rf"(\d+(?:[.,]\d+)?)\s*{TERMINOS_HABITACION}", 0.0),
    (rf"\b({'|'.join(NUMEROS)})\s+{TERMINOS_HABITACION}", 0.0),
    (r"\b(?:apto|apartamento|casa)\s*(\d)\s*/\s*\d", 0.0),
]
PATRONES_BANO = [
    (rf"(\d+(?:[.,]\d+)?)\s*{TERMINOS_BANO}\s*y\s+medio", 0.5),
    (rf"(\d+(?:[.,]\d+)?)\s*{TERMINOS_BANO}(?!\s*s?\s*(?:y\s+)?medio)", 0.0),
    (rf"\b({'|'.join(NUMEROS)})\s+{TERMINOS_BANO}", 0.0),
    (r"medio\s+bano", 0.5),
]


def normalizar(texto) -> str:
    """Minusculas sin tildes; la evidencia conserva el texto original aparte."""
    base = str(texto or "").lower()
    descompuesto = unicodedata.normalize("NFD", base)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def convertir(bruto: str, extra: float) -> float:
    """Valor de una coincidencia: el numero capturado (o `extra` si no lo hay).

    `extra` es la fraccion que se suma cuando el patron la indica ("y medio",
    "medio bano"); los patrones sin fraccion usan 0.0 y devuelven el numero tal
    cual, sin inflarlo.
    """
    if bruto is None:
        return extra
    if bruto in NUMEROS:
        return float(NUMEROS[bruto]) + extra
    return float(bruto.replace(",", ".")) + extra


def extraer_cantidad(texto: str, patrones) -> tuple[float | None, str, list[float]]:
    """Devuelve (valor, fragmento de evidencia, todos los valores distintos).

    Se queda con la primera aparicion explicita; los demas valores distintos se
    devuelven para poder marcar el conflicto sin inventar nada.
    """
    normalizado = normalizar(texto)
    if not normalizado.strip():
        return None, "", []
    valores: list[float] = []
    fragmento = ""
    for patron, extra in patrones:
        coincidencias = list(re.finditer(patron, normalizado))
        if coincidencias and not fragmento:
            fragmento = coincidencias[0].group(0).strip()
        for coincidencia in coincidencias:
            bruto = coincidencia.group(1) if coincidencia.lastindex else None
            valor = convertir(bruto, extra)
            if valor not in valores:
                valores.append(valor)
    if not valores:
        return None, "", []
    return valores[0], fragmento, valores


def slug_desde_url(url: str) -> str:
    ruta = str(url).split("?", 1)[0]
    ultimo = ruta.rsplit("/", 1)[-1]
    sin_id = re.sub(r"-\d{6,10}$", "", ultimo)
    return sin_id.replace("-", " ")


def fecha_snapshot_listado() -> str:
    """Fecha de descarga del listado guardado, tomada del HTML mismo.

    El timestamp de Cloudflare (`__CF$cv$params` -> `t`, base64 con epoch) marca
    el momento en que el servidor renderizo la pagina; los `mtime` de los
    archivos corroboran el mismo dia.
    """
    for pagina in sorted(PAGINAS_DIR.glob("revolico_pagina_*.html")):
        html = pagina.read_text(encoding="utf-8", errors="replace")
        coincidencia = re.search(r"__CF\$cv\$params=\{r:'[^']*',t:'([^']+)'", html)
        if coincidencia:
            epoch = int(base64.b64decode(coincidencia.group(1)).decode())
            return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")
    return ""


def procesar(fila) -> dict:
    titulo = fila.titulo
    descripcion = fila.descripcion
    slug = slug_desde_url(fila.url)

    hab_desc, ev_hab_desc, vals_hab_desc = extraer_cantidad(descripcion, PATRONES_HABITACION)
    ban_desc, ev_ban_desc, vals_ban_desc = extraer_cantidad(descripcion, PATRONES_BANO)
    hab_titulo, ev_hab_titulo, vals_hab_titulo = extraer_cantidad(titulo, PATRONES_HABITACION)
    ban_titulo, ev_ban_titulo, vals_ban_titulo = extraer_cantidad(titulo, PATRONES_BANO)
    hab_slug, _, vals_hab_slug = extraer_cantidad(slug, PATRONES_HABITACION)
    ban_slug, _, vals_ban_slug = extraer_cantidad(slug, PATRONES_BANO)

    # Evidencia por campo: la descripcion manda; si no menciona la cantidad, el
    # titulo del propio anuncio ("Apto 1/4 ...") aporta el valor con su cita.
    evidencia = []
    if ev_hab_desc:
        evidencia.append(f"habitaciones='{ev_hab_desc}'")
    elif ev_hab_titulo and hab_titulo is not None:
        evidencia.append(f"habitaciones_titulo='{ev_hab_titulo}'")
    if ev_ban_desc:
        evidencia.append(f"banos='{ev_ban_desc}'")
    elif ev_ban_titulo and ban_titulo is not None:
        evidencia.append(f"banos_titulo='{ev_ban_titulo}'")

    conflictos = []
    if hab_desc is not None and hab_titulo is not None and hab_desc != hab_titulo:
        conflictos.append(f"habitaciones titulo={hab_titulo:g} descripcion={hab_desc:g}")
    if ban_desc is not None and ban_titulo is not None and ban_desc != ban_titulo:
        conflictos.append(f"banos titulo={ban_titulo:g} descripcion={ban_desc:g}")
    if len(vals_hab_desc) > 1:
        conflictos.append("habitaciones descripcion=" + "/".join(f"{v:g}" for v in vals_hab_desc))
    if len(vals_ban_desc) > 1:
        conflictos.append("banos descripcion=" + "/".join(f"{v:g}" for v in vals_ban_desc))

    return {
        "habitaciones_descripcion": hab_desc,
        "banos_descripcion": ban_desc,
        "habitaciones_titulo": hab_titulo,
        "banos_titulo": ban_titulo,
        "habitaciones_slug": hab_slug,
        "banos_slug": ban_slug,
        "evidencia_detalle": "; ".join(evidencia),
        "conflicto_detalle": "; ".join(conflictos),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, help="Destino concreto; por defecto uno fechado.")
    args = parser.parse_args()

    masters = sorted(MASTER_DIR.glob("dataset_maestro_*.csv"))
    metadatos_files = sorted(META_DIR.glob("metadatos_revolico_*.csv"))
    if not masters or not metadatos_files:
        raise SystemExit("Falta el maestro o los metadatos; ejecuta integrar_fuentes.py y extraer_metadatos_revolico.py")

    maestro = pd.read_csv(masters[-1], dtype=str).fillna("")
    revolico = maestro.loc[maestro["fuente"].eq("Revolico"), ["id_local", "url", "titulo"]].drop_duplicates("url")
    metadatos = pd.read_csv(metadatos_files[-1], dtype=str).fillna("")
    metadatos = metadatos.drop_duplicates(subset=["url"], keep="last")

    base = revolico.merge(
        metadatos[["url", "estado", "descripcion", "fecha_extraccion"]],
        on="url", how="left",
    ).fillna("")
    base["estado"] = base["estado"].replace("", "no_consultado")

    snapshot = fecha_snapshot_listado()
    detalles = pd.DataFrame([procesar(fila) for fila in base.itertuples(index=False)])
    salida = pd.concat([base.reset_index(drop=True), detalles], axis=1)
    salida.insert(0, "fecha_snapshot_listado", snapshot)

    destino = args.salida or OUT_DIR / f"detalle_anuncios_revolico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(destino, index=False, encoding="utf-8-sig")

    publicados = salida["estado"].eq("publicado")
    print(f"Salida: {destino}")
    print(f"Anuncios: {len(salida)} (publicados {int(publicados.sum())}, no publicados {int((~publicados).sum())})")
    print(f"Snapshot del listado: {snapshot}")
    for campo in ("habitaciones_descripcion", "banos_descripcion", "habitaciones_slug", "banos_slug"):
        print(f"  {campo}: {int(salida[campo].notna().sum())}")
    print(f"Conflictos titulo vs descripcion: {int(salida['conflicto_detalle'].str.contains('titulo').sum())}")


if __name__ == "__main__":
    main()
