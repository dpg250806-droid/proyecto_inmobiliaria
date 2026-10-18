#!/usr/bin/env python3
"""Extrae municipio, fecha y descripcion de cada anuncio individual de Revolico.

La tarjeta guardada en `paginas_revolico/` solo contiene imagen, precio, titulo y
enlace: el municipio y la fecha no estan en el HTML de listado. Si existen, estan
en la pagina del anuncio, dentro de `__NEXT_DATA__` -> `props.pageProps.__APOLLO_STATE__`:

- municipio y provincia: referencias `MunicipalityType:<id>` / `ProvinceType:<id>`;
- fecha: `updatedOnByUser`, la fecha exacta de la ultima actualizacion, que es la
  que el sitio muestra como "hace X dias"; NO es necesariamente la fecha de creacion;
- descripcion completa, precio y moneda vigentes en la pagina, estado y `isSold`.

Para cada URL del dataset maestro consulta la pagina con reintentos y espera
cortes, y guarda la evidencia. Si el anuncio esta despublicado o la pagina no
responde, se registra el estado; no se inventa ningun valor.

Salida: `outputs/metadatos_revolico/metadatos_revolico_<marca>.csv`, incrementado
fila a fila y reanudable con `--reanudar <ruta>`. `integrar_fuentes.py` aplica el
fichero mas reciente con `aplicar_metadatos_revolico()`.

No modifica el maestro ni los CSV originales.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
OUT_DIR = ROOT / "outputs" / "metadatos_revolico"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TIMEOUT = 30
ESPERA = 0.6

# Los 15 municipios de La Habana, para buscar en el texto cuando la pagina no
# trae el campo estructurado. Palabras comunes ("playa", "cerro", "regla") pueden
# dar falsos positivos, por eso el metodo queda registrado en `metodo_municipio`.
MUNICIPIOS_LA_HABANA = {
    "arroyo naranjo": "Arroyo Naranjo",
    "boyeros": "Boyeros",
    "centro habana": "Centro Habana",
    "cerro": "Cerro",
    "cotorro": "Cotorro",
    "diez de octubre": "Diez de Octubre",
    "10 de octubre": "Diez de Octubre",
    "guanabacoa": "Guanabacoa",
    "habana del este": "Habana del Este",
    "la habana del este": "Habana del Este",
    "habana vieja": "Habana Vieja",
    "la habana vieja": "Habana Vieja",
    "la lisa": "La Lisa",
    "marianao": "Marianao",
    "playa": "Playa",
    "plaza de la revolucion": "Plaza de la Revolución",
    "regla": "Regla",
    "san miguel del padron": "San Miguel del Padrón",
}

ESTADOS_TERMINALES = {"publicado", "despublicado"}


def es_terminal(estado: str) -> bool:
    """True si la consulta ya dio una respuesta definitiva del sitio.

    Los anuncios publicados, despublicados o borrados son definitivos: la pagina
    respondio. Los fallos de red (`http_XXX`, `error_http`, `sin_datos`) se
    reintentan al reanudar.
    """
    texto = str(estado or "").strip().lower()
    return texto in ESTADOS_TERMINALES or texto.startswith("anuncio_inexistente")


def limpiar(texto) -> str:
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def quitar_tildes(texto: str) -> str:
    tabla = str.maketrans("áéíóúüñ", "aeiouun")
    return texto.translate(tabla).lower()


def buscar_municipio_en_texto(texto: str) -> str:
    """Busca un municipio de La Habana como palabra entera en titulo/descripcion.

    Devuelve el municipio unico encontrado o vacio. Varios coincidentes cuentan
    como ambiguos y se descartan; el metodo queda registrado por el llamador.
    """
    normalizado = quitar_tildes(limpiar(texto))
    encontrados = set()
    for clave, municipio in MUNICIPIOS_LA_HABANA.items():
        if re.search(rf"(?<!\w){re.escape(clave)}(?!\w)", normalizado):
            encontrados.add(municipio)
    return encontrados.pop() if len(encontrados) == 1 else ""


def parsear_pagina_anuncio(html: str) -> dict:
    """Extrae los metadatos del `__APOLLO_STATE__` de una pagina de anuncio."""
    coincidencia = re.search(r'<script[^>]*__NEXT_DATA__[^>]*>(.*?)</script>', html, re.S)
    if not coincidencia:
        if "Anuncio despublicado" in html:
            return {"estado": "despublicado"}
        return {"estado": "sin_datos"}
    datos = json.loads(coincidencia.group(1))
    props = datos.get("props", {}).get("pageProps", {})
    apollo = props.get("__APOLLO_STATE__", {}) or {}
    anuncio = next(
        (valor for clave, valor in apollo.items()
         if isinstance(valor, dict) and clave.startswith("AdType:")),
        None,
    )
    if anuncio is None:
        if props.get("errorCode"):
            return {"estado": f"anuncio_inexistente_{props['errorCode']}"}
        if "Anuncio despublicado" in html:
            return {"estado": "despublicado"}
        return {"estado": "sin_datos"}

    ref_municipio = (anuncio.get("municipality") or {}).get("__ref")
    ref_provincia = (anuncio.get("province") or {}).get("__ref")
    municipio = limpiar(apollo.get(ref_municipio, {}).get("name")) if ref_municipio else ""
    provincia = limpiar(apollo.get(ref_provincia, {}).get("name")) if ref_provincia else ""

    titulo = limpiar(anuncio.get("title"))
    descripcion = limpiar(anuncio.get("description"))

    metodo_municipio = "apollo" if municipio else ""
    if not municipio:
        municipio = buscar_municipio_en_texto(f"{titulo} {descripcion}")
        if municipio:
            metodo_municipio = "texto_titulo_o_descripcion"

    estado = limpiar(anuncio.get("status")).lower()
    estado = {"published": "publicado", "unpublished": "despublicado"}.get(estado, estado or "publicado")

    return {
        "estado": estado,
        "titulo_pagina": titulo,
        "descripcion": descripcion,
        "precio_pagina": limpiar(f"{anuncio.get('price')} {anuncio.get('currency')}".replace("None", "")),
        "municipio": municipio,
        "metodo_municipio": metodo_municipio,
        "provincia": provincia,
        "fecha_updated_on": limpiar(anuncio.get("updatedOnByUser")),
        "vendido": anuncio.get("isSold"),
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
    return parsear_pagina_anuncio(html)


def urls_del_maestro() -> pd.DataFrame:
    archivos = sorted(MASTER_DIR.glob("dataset_maestro_*.csv"))
    if not archivos:
        raise FileNotFoundError("No hay dataset maestro; ejecuta integrar_fuentes.py")
    maestro = pd.read_csv(archivos[-1], dtype=str).fillna("")
    revolico = maestro.loc[maestro["fuente"].eq("Revolico"), ["id_local", "url"]].drop_duplicates("url")
    return revolico.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--espera", type=float, default=ESPERA, help="segundos entre peticiones")
    parser.add_argument("--limite", type=int, default=0, help="procesar solo las primeras N URLs (0 = todas)")
    parser.add_argument("--reanudar", type=Path, help="CSV existente al que anadir resultados pendientes")
    argumentos = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pendientes = urls_del_maestro()
    hechos: set[str] = set()
    if argumentos.reanudar:
        if not argumentos.reanudar.exists():
            raise SystemExit(f"No existe el archivo a reanudar: {argumentos.reanudar}")
        previo = pd.read_csv(argumentos.reanudar, dtype=str).fillna("")
        # Solo se saltan los estados terminales; los fallos de red se reintentan.
        hechos = set(previo.loc[previo["estado"].map(es_terminal), "url"])
        salida = argumentos.reanudar
        print(f"Reanudando {salida.name}: {len(hechos)} anuncios ya resueltos")
    else:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        salida = OUT_DIR / f"metadatos_revolico_{marca}.csv"

    pendientes = pendientes[~pendientes["url"].isin(hechos)]
    if argumentos.limite:
        pendientes = pendientes.head(argumentos.limite)
    if pendientes.empty:
        print("Nada pendiente por consultar")
        return

    columnas = [
        "fecha_extraccion", "id_local", "url", "estado", "titulo_pagina", "municipio",
        "metodo_municipio", "provincia", "fecha_updated_on", "precio_pagina", "vendido",
        "descripcion",
    ]
    sesion = requests.Session()
    escribir_cabecera = not salida.exists()
    for numero, fila in enumerate(pendientes.itertuples(index=False), start=1):
        datos = obtener(fila.url, sesion)
        registro = {
            "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_local": fila.id_local,
            "url": fila.url,
            "titulo_pagina": datos.get("titulo_pagina", ""),
            "descripcion": datos.get("descripcion", ""),
            "precio_pagina": datos.get("precio_pagina", ""),
            "municipio": datos.get("municipio", ""),
            "metodo_municipio": datos.get("metodo_municipio", ""),
            "provincia": datos.get("provincia", ""),
            "fecha_updated_on": datos.get("fecha_updated_on", ""),
            "vendido": datos.get("vendido", ""),
            "estado": datos.get("estado", "sin_datos"),
        }
        with salida.open("a", encoding="utf-8-sig", newline="") as handle:
            pd.DataFrame([registro], columns=columnas).to_csv(handle, header=escribir_cabecera, index=False)
        escribir_cabecera = False
        print(
            f"[{numero:03d}/{len(pendientes)}] {registro['estado']:<16} "
            f"{registro['municipio']:<20} {registro['fecha_updated_on'][:10]:<10} {fila.url[-42:]}"
        )
        time.sleep(argumentos.espera)

    tabla = pd.read_csv(salida, dtype=str).fillna("")
    print()
    print(f"Salida: {salida} ({len(tabla)} filas)")
    print("Estados:", dict(tabla["estado"].value_counts()))
    print("Con municipio:", int(tabla["municipio"].ne("").sum()))
    print("Con fecha:", int(tabla["fecha_updated_on"].ne("").sum()))


if __name__ == "__main__":
    main()
