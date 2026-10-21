#!/usr/bin/env python3
"""Integra fuentes inmobiliarias cubanas en un dataset maestro no destructivo.

Uso:
    python integrar_fuentes.py
    python integrar_fuentes.py --sin-dedup
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re

import numpy as np
import pandas as pd

from precio_moneda import detalle_analisis, precios_analisis
from ubicaciones import homologar_municipio


REPO_ROOT = Path(__file__).resolve().parent
STANDARD_COLUMNS = [
    "fuente",
    "snapshot_origen",
    "id_local",
    "titulo",
    "url",
    "tipo_vivienda",
    "ubicacion_raw",
    "zona_normalizada",
    "habitaciones",
    "banos",
    "superficie_m2",
    "precio_original",
    "moneda",
    "precio_sospechoso",
    "fecha_publicacion",
    "fecha_descarga",
    "garaje",
    "piscina",
    "terraza",
    "patio",
    "balcon",
    "jardin",
    "canal",
    "agencia_observada",
    "calidad_metadatos",
    "texto_evidencia",
    "observacion",
]


def normalizar_texto(value):
    if pd.isna(value):
        return value
    return str(value).strip().replace("  ", " ")


def normalizar_zona(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i")
    text = text.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    text = re.sub(r"\s+", " ", text)
    return text


def clasificar_tipo_vivienda(titulo) -> str | None:
    """Clasifica el tipo de vivienda a partir del titulo completo de Revolico.

    El CSV de Revolico no trae columna de tipo. Antes se usaba la primera
    palabra del titulo, lo que convertia precios ("30.000 USD ...") y
    telefonos en tipos de vivienda; ahora se buscan palabras clave en todo
    el titulo con la misma precedencia que `limpiar_revolico.py`
    (penthouse > casa > apartamento/apto) y, si no hay titulo o no se
    reconoce el tipo, se devuelve `None`/`no_clasificado` sin inventar datos.
    """
    if titulo is None or pd.isna(titulo):
        return None
    texto = str(titulo).strip().lower()
    if not texto:
        return None
    if "penthouse" in texto:
        return "penthouse"
    if re.search(r"\bcasa\b", texto):
        return "casa"
    if re.search(r"apart|apto", texto):
        return "apartamento"
    return "no_clasificado"


def normalizar_precio(value, moneda) -> tuple[float | None, bool]:
    """Devuelve (precio_numerico, sospechoso) sin borrar valores atipicos."""
    if pd.isna(value):
        return None, True

    try:
        number = float(value)
    except (TypeError, ValueError):
        parsed = re.search(r"(\d[\d.,]*)", str(value))
        number = float(parsed.group(1).replace(".", "").replace(",", ".")) if parsed else None

    if number is None:
        return None, True
    if not np.isfinite(number):
        return None, True
    if number <= 0:
        return number, True
    if number == 1:
        return number, True
    if number > 1_000_000:
        return number, True
    if pd.isna(moneda) or str(moneda).strip().lower() in {"", "nan", "none"}:
        return number, True
    return number, False


def quality_score(row, required_fields):
    return sum(pd.notna(row.get(field)) and str(row.get(field)).strip() != "" for field in required_fields)


def dataframe_revolico(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    rows = []
    required = ["tipo_vivienda", "ubicacion_raw", "habitaciones", "precio_original", "moneda"]
    for idx, item in source.iterrows():
        price, suspicious = normalizar_precio(item.get("precio", ""), item.get("moneda", ""))
        if (not suspicious) and str(item.get("moneda", "")).strip().upper() == "CUP":
            suspicious = True
        rows.append(
            {
                "fuente": "Revolico",
                "snapshot_origen": str(path.name),
                "id_local": f"rev_{idx + 1:06d}_{pd.notna(item.get('url')) and item['url'][:60] or idx}",
                "titulo": normalizar_texto(item.get("titulo", "")),
                "url": normalizar_texto(item.get("url", "")),
                "tipo_vivienda": clasificar_tipo_vivienda(item.get("titulo", None)),
                "ubicacion_raw": normalizar_texto(item.get("municipio", None)),
                "zona_normalizada": normalizar_zona(item.get("municipio", None)),
                "habitaciones": pd.to_numeric(item.get("habitaciones", None), errors="coerce"),
                "banos": np.nan,
                "superficie_m2": None,
                "precio_original": price if price is not None else item.get("precio", None),
                "moneda": (str(item.get("moneda", "")).strip().upper() if pd.notna(item.get("moneda", None)) else None),
                "precio_sospechoso": suspicious,
                "fecha_publicacion": None,
                "fecha_descarga": pd.Timestamp.now().isoformat(timespec="seconds"),
                "garaje": None,
                "piscina": None,
                "terraza": None,
                "patio": None,
                "balcon": None,
                "jardin": None,
                "canal": "clasificado_informal",
                "agencia_observada": "desconocido",
                "sirve_proyecto": normalizar_texto(item.get("sirve_proyecto", None)),
                "calidad_metadatos": 0,
                "_required_fields": required,
                "texto_evidencia": normalizar_texto(item.get("texto_tarjeta", None)),
                "observacion": "Municipio/habitaciones derivados del titulo/formulario del extractor; texto_tarjeta puede contener varios anuncios y no se usa para variables individuales.",
            }
        )
    frame = pd.DataFrame(rows)
    frame["calidad_metadatos"] = frame.apply(lambda r: quality_score(r, required), axis=1)
    return frame[STANDARD_COLUMNS]


def dataframe_cubisima(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    rows = []
    required = ["tipo_vivienda", "ubicacion_raw", "habitaciones", "banos", "precio_original", "moneda"]
    feature_map = {
        "garaje": "garaje",
        "piscina": "piscina",
        "terraza": "terraza",
        "patio": "patio",
        "balcon": "balcon",
        "jardin": "jardin",
    }
    for idx, item in source.iterrows():
        price, suspicious = normalizar_precio(item.get("precio", None), item.get("moneda", None))
        ubi = normalizar_texto(item.get("zona", None))
        t = normalizar_texto(item.get("tipo", None))
        tipo = t.lower() if pd.notna(t) and t else None
        row = {
            "fuente": "Cubisima",
            "snapshot_origen": str(path.name),
            "id_local": f"cubisima_{idx + 1:06d}",
            "titulo": normalizar_texto(item.get("titulo", "")),
            "url": normalizar_texto(item.get("url", "")),
            "tipo_vivienda": tipo,
            "ubicacion_raw": ubi,
            "zona_normalizada": normalizar_zona(ubi),
            "habitaciones": pd.to_numeric(item.get("habitaciones", None), errors="coerce"),
            "banos": pd.to_numeric(item.get("banos", None), errors="coerce"),
            "superficie_m2": None,
            "precio_original": price if price is not None else item.get("precio", None),
            "moneda": (str(item.get("moneda", "")).strip().upper() if pd.notna(item.get("moneda", None)) else None),
            "precio_sospechoso": suspicious,
            "fecha_publicacion": normalizar_texto(item.get("fecha", None)),
            "fecha_descarga": pd.Timestamp.now().isoformat(timespec="seconds"),
            "canal": "plataforma_clasificados",
            "agencia_observada": "desconocido",
            "sirve_proyecto": None,
            "texto_evidencia": normalizar_texto(item.get("texto_tarjeta", None)),
            "observacion": "Precio recibido desde archivo local Cubisima; Cubisima se usa como fuente complementaria mas rica en banos y zona. Factores como garaje/piscina provienen de booleanos del extractor.",
        }
        for target, source_field in feature_map.items():
            raw = item.get(source_field, None)
            if pd.isna(raw):
                row[target] = None
            elif str(raw).strip().lower() in {"1", "true", "si", "sí", "yes"}:
                row[target] = 1
            elif str(raw).strip().lower() in {"0", "false", "no"}:
                row[target] = 0
            else:
                row[target] = pd.to_numeric(raw, errors="coerce")
        row["calidad_metadatos"] = quality_score(row, required)
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame[STANDARD_COLUMNS]


def dataframe_hogarencuba(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    rows = []
    required = ["tipo_vivienda", "ubicacion_raw", "habitaciones", "banos", "superficie_m2", "precio_original", "moneda"]
    feature_map = {"garaje": "garaje", "piscina": "piscina", "terraza": "terraza", "patio": "patio", "balcon": "balcon", "jardin": "jardin"}
    for idx, item in source.iterrows():
        price, suspicious = normalizar_precio(item.get("precio_original", None), item.get("moneda", None))
        if "precio_sospechoso" in source.columns and pd.notna(item.get("precio_sospechoso", None)):
            suspicious = str(item.get("precio_sospechoso")).strip().lower().replace("\u00ed", "i") in {"true", "1", "si", "yes"}
        row = {
            "fuente": "HogarEnCuba",
            "snapshot_origen": str(path.name),
            "id_local": (str(item.get("id_local", "")).strip() or f"hec_{idx + 1:06d}"),
            "titulo": normalizar_texto(item.get("titulo", "")),
            "url": normalizar_texto(item.get("url", "")),
            "tipo_vivienda": normalizar_texto(item.get("tipo_vivienda", None)),
            "ubicacion_raw": normalizar_texto(item.get("ubicacion_raw", None)),
            "zona_normalizada": normalizar_zona(item.get("ubicacion_raw", None)),
            "habitaciones": pd.to_numeric(item.get("habitaciones", None), errors="coerce"),
            "banos": pd.to_numeric(item.get("banos", None), errors="coerce"),
            "superficie_m2": pd.to_numeric(item.get("superficie_m2", None), errors="coerce"),
            "precio_original": price if price is not None else item.get("precio_original", None),
            "moneda": (str(item.get("moneda", "")).strip().upper() if pd.notna(item.get("moneda", None)) else None),
            "precio_sospechoso": suspicious,
            "fecha_publicacion": normalizar_texto(item.get("fecha_publicacion", None)),
            "fecha_descarga": pd.Timestamp.now().isoformat(timespec="seconds"),
            "garaje": pd.to_numeric(item.get("garaje", None), errors="coerce"),
            "piscina": pd.to_numeric(item.get("piscina", None), errors="coerce"),
            "terraza": pd.to_numeric(item.get("terraza", None), errors="coerce"),
            "patio": pd.to_numeric(item.get("patio", None), errors="coerce"),
            "balcon": pd.to_numeric(item.get("balcon", None), errors="coerce"),
            "jardin": pd.to_numeric(item.get("jardin", None), errors="coerce"),
            "canal": normalizar_texto(item.get("canal", None)) or "plataforma_estructurada",
            "agencia_observada": normalizar_texto(item.get("agencia_observada", None)) or "no verificado (plataforma individual)",
            "sirve_proyecto": None,
            "texto_evidencia": normalizar_texto(item.get("texto_evidencia", None)),
            "observacion": "Fuente formal/estructurada con m2, banos y municipio; los anuncios se parsean desde fichas individuales.",
        }
        row["calidad_metadatos"] = quality_score(row, required)
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame[STANDARD_COLUMNS]


def cubisima_source_path(root: Path) -> Path:
    corrected = sorted((root / "outputs" / "cubisima").glob("viviendas_cubisima_reprocesada_*.csv"))
    return corrected[-1] if corrected else root / "viviendas_cubisima.csv"


def hogarencuba_source_path(root: Path) -> Path | None:
    directory = root / "outputs" / "hogarencuba"
    candidates = []
    for path in directory.glob("viviendas_hogarencuba_*.csv"):
        try:
            if path.stat().st_size > 0:
                row_count = len(pd.read_csv(path, dtype=str))
                if row_count:
                    candidates.append((row_count, path.stat().st_mtime, path))
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
            continue
    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


VEREDICTOS_EXCLUYENTES = {
    "alquiler",
    "despublicado",
    "error",
    "no_verificable",
    "otro",
    "permuta",
    "producto",
}

# Veredictos que identifican anuncios que no son venta de vivienda:
# productos, permutas (cambio, no venta), locales u otros inmuebles no
# residenciales y alquileres. El scraper del proyecto describe el mercado
# residencial en venta, asi que estos anuncios se excluyen del dataset.
NO_RESIDENCIALES = {"alquiler", "otro", "permuta", "producto"}


def excluir_no_residenciales(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa los anuncios que no son vivienda en venta (no destructivo).

    Devuelve `(dataset_sin_no_residenciales, excluidos)`. Los excluidos no se
    destruyen: van a `outputs/integracion/anuncios_no_residenciales_<fecha>.csv`
    con su veredicto y su evidencia, para que la exclusion sea auditable. El
    resto de anuncios conserva intactas todas sus columnas.
    """
    if "veredicto_revision" not in frame.columns:
        return frame, frame.iloc[0:0]
    mascara = frame["veredicto_revision"].fillna("").astype(str).str.strip().str.lower().isin(NO_RESIDENCIALES)
    return frame.loc[~mascara].copy(), frame.loc[mascara].copy()


EXCLUSIONES_ALCANCE_POR_DEFECTO = REPO_ROOT / "revision_manual" / "exclusiones_alcance.csv"


def excluir_fuera_de_alcance(
    frame: pd.DataFrame, ruta: Path | None = EXCLUSIONES_ALCANCE_POR_DEFECTO
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa anuncios fuera de La Habana o que no son una vivienda.

    La lista se versiona en `revision_manual/exclusiones_alcance.csv` y se
    empareja por URL exacta (el `id_local` de Revolico incluye la URL y puede
    cambiar si se reextrae). Devuelve `(dataset_filtrado, excluidos)`; los
    excluidos conservan todas sus columnas y reciben `motivo_alcance`.
    """
    if ruta is None or not Path(ruta).exists() or frame.empty:
        return frame.copy(), frame.iloc[0:0].copy()

    lista = pd.read_csv(ruta, dtype=str).fillna("")
    faltantes = {"url", "motivo"} - set(lista.columns)
    if faltantes:
        raise ValueError(f"{ruta} no tiene las columnas requeridas: {sorted(faltantes)}")
    lista = lista[lista["url"].str.strip().ne("")].copy()
    motivos = (
        lista.drop_duplicates("url").set_index("url")["motivo"].str.strip().to_dict()
    )
    urls = set(motivos)
    mascara = frame["url"].fillna("").astype(str).str.strip().isin(urls)
    excluidos = frame.loc[mascara].copy()
    if not excluidos.empty:
        excluidos["motivo_alcance"] = excluidos["url"].astype(str).str.strip().map(motivos)
    return frame.loc[~mascara].copy(), excluidos


RUTA_ALCANCE_DUDOSO_POR_DEFECTO = REPO_ROOT / "revision_manual" / "alcance_dudoso.csv"


def aplicar_alcance_dudoso(
    frame: pd.DataFrame, ruta: Path | None = RUTA_ALCANCE_DUDOSO_POR_DEFECTO
) -> pd.DataFrame:
    """Marca los anuncios de alcance dudoso que se conservan en el analisis.

    Decision de la investigadora (20/10/2026): todo lo que sea venta de inmueble
    es valido, por lo que estas fichas (fincas, hostales, casas con bar o
    restaurante, almacenes, local adaptado) se mantienen en el maestro. La marca
    `alcance_dudoso` permite medir la sensibilidad de los resultados sin volver
    a integrar el maestro.
    """
    frame = frame.copy()
    frame["alcance_dudoso"] = False
    frame["motivo_alcance_dudoso"] = ""
    if ruta is None or not Path(ruta).exists() or frame.empty:
        return frame
    lista = pd.read_csv(ruta, dtype=str).fillna("")
    if "url" not in lista.columns:
        raise ValueError(f"{ruta} no tiene la columna 'url'")
    motivos = (
        lista.drop_duplicates("url").set_index("url")["motivo"].str.strip().to_dict()
        if "motivo" in lista.columns
        else {}
    )
    urls = frame["url"].fillna("").astype(str).str.strip()
    mascara = urls.isin(set(motivos))
    frame.loc[mascara, "alcance_dudoso"] = True
    frame.loc[mascara, "motivo_alcance_dudoso"] = urls[mascara].map(motivos)
    return frame


RUTAS_REVISION_POR_DEFECTO = (
    # Revision de precios raros (<1.000) y de alquileres publicados en el
    # catalogo de venta: se resolvio con la ficha individual de cada anuncio
    # (20/10/2026) y va primero porque es posterior y mas especifica.
    REPO_ROOT / "revision_manual" / "precios_bajos_1000.csv",
    REPO_ROOT / "revision_manual" / "precios_bajos.csv",
    REPO_ROOT / "revision_manual" / "precios_ausentes.csv",
)


def aplicar_veredictos_revision(
    frame: pd.DataFrame, ruta: Path | None = None, adicionales: list[Path] | None = None
) -> pd.DataFrame:
    """Aplica las revisiones de precios sobre el maestro (no destructivo).

    Lee una o varias listas de revision: por defecto `revision_manual/precios_bajos.csv`
    (revision uno a uno de precios bajos) y `revision_manual/precios_ausentes.csv`
    (recuperacion de precios en texto y consulta de paginas sin precio); o los
    archivos que se pasen en `ruta` y `adicionales`.

    Por cada anuncio revisado:
    - registra su veredicto en `veredicto_revision` (si varias listas lo
      informan, gana la primera: asi se conserva la revision manual original);
    - marca `precio_sospechoso` solo si el veredicto esta en
      `VEREDICTOS_EXCLUYENTES`;
    - si la revision trajo un precio verificado en la descripcion o en el
      titulo, lo registra en `precio_reextraido` con su moneda y su evidencia.

    No se borra ni se corrige ningun valor original: quien decide que valor se
    analiza es `precio_analisis` (ver `precios_analisis`).
    """
    if ruta is None:
        rutas = [archivo for archivo in RUTAS_REVISION_POR_DEFECTO if archivo.exists()]
        rutas += list(adicionales or [])
    else:
        rutas = [ruta, *(adicionales or [])]
    frame = frame.copy()
    frame["veredicto_revision"] = ""
    frame["precio_reextraido"] = np.nan
    frame["moneda_reextraida"] = ""
    frame["evidencia_precio"] = ""

    leidas: list[str] = []
    veredictos: dict[str, str] = {}
    precios: dict[str, float] = {}
    monedas: dict[str, str] = {}
    evidencias: dict[str, str] = {}
    for archivo in rutas:
        if not archivo.exists():
            continue
        revision = pd.read_csv(archivo, dtype=str).fillna("")
        if "url" not in revision or "veredicto" not in revision:
            continue
        revision["veredicto"] = revision["veredicto"].str.strip().str.lower()
        leidas.append(archivo.name)

        # Reextraccion: si la revision registro un precio verificado en la
        # descripcion o en el titulo, se guarda como medida alternativa con su
        # evidencia. El campo publicado no se corrige: `precio_analisis` decide.
        if "precio_en_descripcion" in revision:
            revisados = revision.copy()
            if "moneda_en_descripcion" not in revisados:
                revisados["moneda_en_descripcion"] = ""
            if "observacion" not in revisados:
                revisados["observacion"] = ""
            revisados["precio_verificado"] = pd.to_numeric(
                revisados["precio_en_descripcion"], errors="coerce"
            )
            revisados = revisados[
                revisados["precio_verificado"].notna() & revisados["url"].ne("")
            ].copy()
            # Cada URL conserva el primer precio registrado (la revision manual
            # original tiene prioridad sobre las recuperaciones posteriores).
            for url, precio in zip(revisados["url"], revisados["precio_verificado"]):
                precios.setdefault(url, precio)
            for url, moneda in zip(revisados["url"], revisados["moneda_en_descripcion"].str.upper()):
                monedas.setdefault(url, moneda)
            for url, cita in zip(revisados["url"], revisados["observacion"]):
                evidencias.setdefault(url, cita)

        # Veredictos: si varias listas informan el mismo URL, gana la primera.
        for url, veredicto in zip(revision["url"], revision["veredicto"]):
            if url and veredicto:
                veredictos.setdefault(url, veredicto)

    if precios:
        con_precio = frame["url"].isin(precios)
        frame.loc[con_precio, "precio_reextraido"] = frame.loc[con_precio, "url"].map(precios)
        frame.loc[con_precio, "moneda_reextraida"] = frame.loc[con_precio, "url"].map(monedas)
        frame.loc[con_precio, "evidencia_precio"] = frame.loc[con_precio, "url"].map(evidencias)
        print(
            f"Reextraccion manual de precio: {int(con_precio.sum())} anuncios con "
            "precio verificado en la fuente"
        )

    if not veredictos:
        return frame
    afectados = frame["url"].isin(veredictos)
    frame.loc[afectados, "veredicto_revision"] = frame.loc[afectados, "url"].map(veredictos)
    excluyentes = afectados & frame["veredicto_revision"].isin(VEREDICTOS_EXCLUYENTES)
    frame.loc[excluyentes, "precio_sospechoso"] = True
    print(
        f"Revision de precios: {int(afectados.sum())} anuncios con veredicto "
        f"(listas: {', '.join(leidas)})"
    )
    return frame


def parsear_fecha_exacta(valor: str):
    """Devuelve la fecha YYYY-MM-DD si el valor es una fecha exacta, si no None.

    Acepta ISO (`2026-09-19T17:30:20.821Z`) y `dd/mm/yyyy`; rechaza fechas
    relativas ("Actualizado: hace 2 anos"), que no confirman un dia.
    """
    texto = str(valor or "").strip()
    if not texto:
        return None
    coincidencia = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
    if coincidencia:
        return coincidencia.group(0)
    coincidencia = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", texto)
    if coincidencia:
        dia, mes, anio = coincidencia.groups()
        return f"{anio}-{int(mes):02d}-{int(dia):02d}"
    return None


def aplicar_metadatos_revolico(
    frame: pd.DataFrame, ruta: Path | None = None
) -> pd.DataFrame:
    """Anade municipio y fecha verificados en la pagina individual de Revolico.

    La tarjeta del listado guardado no contiene municipio ni fecha: ambos viven en
    la pagina del anuncio (`__APOLLO_STATE__`). `extraer_metadatos_revolico.py`
    consulta cada URL y guarda la evidencia en `outputs/metadatos_revolico/`; aqui
    se aplica el fichero mas reciente por URL.

    Columnas nuevas: `municipio_reextraido` (campo estructurado o texto del
    anuncio, con su metodo), `fecha_reextraida` (la `updatedOnByUser` que el sitio
    muestra como "hace X dias"; es fecha de actualizacion, no de creacion),
    `estado_anuncio`, `vendido` y `evidencia_metadatos`. No se corrige
    `ubicacion_raw`: quien decide que valor se analiza es `ubicacion_analisis`.
    """
    frame = frame.copy()
    frame["municipio_reextraido"] = ""
    frame["metodo_municipio"] = ""
    frame["fecha_reextraida"] = ""
    frame["estado_anuncio"] = ""
    frame["vendido"] = ""
    frame["evidencia_metadatos"] = ""
    if ruta is None:
        candidatos = sorted((REPO_ROOT / "outputs" / "metadatos_revolico").glob("metadatos_revolico_*.csv"))
        if not candidatos:
            return frame
        ruta = candidatos[-1]
    if not ruta.exists():
        return frame
    metadatos = pd.read_csv(ruta, dtype=str).fillna("")
    # Ultima consulta por URL gana, por si el archivo acumula reintentos.
    metadatos = metadatos.drop_duplicates(subset=["url"], keep="last")
    if metadatos.empty or "url" not in metadatos:
        return frame
    indices = frame.index[frame["url"].isin(set(metadatos["url"]))]
    if indices.empty:
        return frame
    por_url = metadatos.set_index("url")
    correspondencia = frame.loc[indices, "url"]
    frame.loc[indices, "municipio_reextraido"] = correspondencia.map(por_url["municipio"])
    frame.loc[indices, "metodo_municipio"] = correspondencia.map(por_url["metodo_municipio"])
    frame.loc[indices, "fecha_reextraida"] = correspondencia.map(por_url["fecha_updated_on"])
    frame.loc[indices, "estado_anuncio"] = correspondencia.map(por_url["estado"])
    frame.loc[indices, "vendido"] = correspondencia.map(por_url["vendido"])
    frame.loc[indices, "evidencia_metadatos"] = correspondencia.map(
        lambda url: f"pagina_anuncio; consulta={ruta.stem}; url={url}"
    )
    print(
        f"Metadatos de pagina de anuncio aplicados: {len(indices)} anuncios "
        f"de Revolico (fuente: {ruta.relative_to(REPO_ROOT) if ruta.is_relative_to(REPO_ROOT) else ruta})"
    )
    return frame


def aplicar_detalle_anuncios(
    frame: pd.DataFrame, ruta: Path | None = None
) -> pd.DataFrame:
    """Anade habitaciones y banos leidos del texto de cada anuncio de Revolico.

    `extraer_detalle_anuncios_revolico.py` busca la cantidad escrita por el
    anunciante en descripcion, titulo y enlace (slug), con patrones
    conservadores; aqui se aplican las columnas por URL sin tocar el campo
    publicado. Si la descripcion no menciona la cantidad, se toma el valor del
    titulo del anuncio y `evidencia_detalle` indica de que campo salio cada
    valor. Quien decide que valor se analiza es `detalle_analisis()`.

    Tambien documenta, con evidencia, la ventana de desaparicion de los anuncios
    borrados o despublicados: el listado guardado donde aun aparecian se descargo
    el dia que marca el timestamp de Cloudflare del HTML, y la pagina del anuncio
    se consulto en la fecha de la extraccion de metadatos. La desaparicion
    ocurrio dentro de ese intervalo; el anuncio no se elimina del dataset.
    """
    frame = frame.copy()
    nuevas = [
        "habitaciones_reextraido", "banos_reextraido",
        "habitaciones_slug", "banos_slug",
        "evidencia_detalle", "conflicto_detalle",
        "fecha_ultima_disponibilidad", "ventana_despublicacion",
        "justificacion_disponibilidad",
    ]
    numericas = {"habitaciones_reextraido", "banos_reextraido", "habitaciones_slug", "banos_slug"}
    for columna in nuevas:
        frame[columna] = np.nan if columna in numericas else ""
    if ruta is None:
        candidatos = sorted(
            (REPO_ROOT / "outputs" / "metadatos_revolico").glob("detalle_anuncios_revolico_*.csv")
        )
        if not candidatos:
            return frame
        ruta = candidatos[-1]
    if not ruta.exists():
        return frame
    detalle = pd.read_csv(ruta, dtype=str).fillna("")
    detalle = detalle.drop_duplicates(subset=["url"], keep="last")
    if detalle.empty or "url" not in detalle:
        return frame
    indices = frame.index[frame["url"].isin(set(detalle["url"]))]
    if indices.empty:
        return frame
    por_url = detalle.set_index("url")
    correspondencia = frame.loc[indices, "url"]

    def columna_detalle(origen: str) -> pd.Series:
        """Valores de una columna del CSV de detalle; si no existe, NaN."""
        if origen in por_url.columns:
            return correspondencia.map(por_url[origen])
        return pd.Series(np.nan, index=correspondencia.index)

    # Cadena documentada: la descripcion del anuncio primero y, si no menciona
    # la cantidad, el titulo del propio anuncio ("Apto 1/4" = 1 dormitorio);
    # despues entran el campo publicado y el slug, que resuelve detalle_analisis.
    # Solo se leen columnas presentes en el CSV de detalle.
    for destino, (describir, nombrar) in {
        "habitaciones_reextraido": ("habitaciones_descripcion", "habitaciones_titulo"),
        "banos_reextraido": ("banos_descripcion", "banos_titulo"),
    }.items():
        desde_descripcion = pd.to_numeric(columna_detalle(describir), errors="coerce")
        desde_titulo = pd.to_numeric(columna_detalle(nombrar), errors="coerce")
        frame.loc[indices, destino] = desde_descripcion.where(desde_descripcion.notna(), desde_titulo)
    asignar = {
        "habitaciones_slug": "habitaciones_slug",
        "banos_slug": "banos_slug",
        "evidencia_detalle": "evidencia_detalle",
        "conflicto_detalle": "conflicto_detalle",
    }
    for destino, origen in asignar.items():
        serie = columna_detalle(origen)
        frame.loc[indices, destino] = pd.to_numeric(serie, errors="coerce") if destino in numericas else serie
    # Ventana de desaparicion: solo para los que ya no estan publicados.
    estado = correspondencia.map(por_url["estado"])
    snapshot = correspondencia.map(por_url["fecha_snapshot_listado"])
    consulta = correspondencia.map(por_url["fecha_extraccion"]).astype(str).str.slice(0, 10)
    afectados = estado.index[estado.ne("publicado") & estado.ne("")]
    frame.loc[afectados, "fecha_ultima_disponibilidad"] = snapshot.loc[afectados]
    frame.loc[afectados, "ventana_despublicacion"] = (
        snapshot.loc[afectados] + " a " + consulta.loc[afectados]
    )
    frame.loc[afectados, "justificacion_disponibilidad"] = [
        f"aparecia en el listado guardado del {s}; al consultar la pagina el {c} devolvio {e}"
        for s, c, e in zip(snapshot.loc[afectados], consulta.loc[afectados], estado.loc[afectados])
    ]
    borrados = len(afectados)
    print(
        f"Detalle de anuncios aplicado: {len(indices)} anuncios de Revolico "
        f"({borrados} con ventana de desaparicion documentada; "
        f"fuente: {ruta.relative_to(REPO_ROOT) if ruta.is_relative_to(REPO_ROOT) else ruta})"
    )
    return frame


def ubicacion_analisis(frame: pd.DataFrame) -> tuple[pd.Series, str]:
    """Devuelve (ubicacion de analisis, origen) para cada fila del maestro.

    Reglas: el municipio verificado en la pagina del anuncio (`municipio_reextraido`)
    tiene prioridad sobre el campo publicado (`ubicacion_raw`). Si ambos estan
    vacios, la ubicacion de analisis queda vacia y el origen es `sin_dato`; no se
    imputa ningun municipio.
    """
    indice = frame.index
    reextraida = (
        frame["municipio_reextraido"].fillna("").astype(str).str.strip()
        if "municipio_reextraido" in frame
        else pd.Series("", index=indice)
    )
    publicada = (
        frame["ubicacion_raw"].fillna("").astype(str).str.strip()
        if "ubicacion_raw" in frame
        else pd.Series("", index=indice)
    )
    ubicacion = reextraida.where(reextraida.ne(""), publicada.where(publicada.ne(""))).fillna("")
    origen = pd.Series("sin_dato", index=indice)
    origen.loc[ubicacion.ne("")] = "campo_publicado"
    origen.loc[reextraida.ne("")] = "pagina_anuncio"
    return ubicacion, origen


def integrar(dedup_by_url: bool = True) -> pd.DataFrame:
    root = REPO_ROOT
    revolico_path = root / "anuncios_revolico_procesados.csv"
    cubisima_path = cubisima_source_path(root)
    hogar_path = hogarencuba_source_path(REPO_ROOT)

    if not revolico_path.exists():
        raise FileNotFoundError(revolico_path)
    if not cubisima_path.exists():
        raise FileNotFoundError(cubisima_path)

    rev = dataframe_revolico(revolico_path)
    cub = dataframe_cubisima(cubisima_path)
    frames = [rev, cub]
    if hogar_path is not None:
        hog = dataframe_hogarencuba(hogar_path)
        frames.append(hog)
    merged = pd.concat(frames, ignore_index=True)

    if dedup_by_url:
        merged["_quality_key"] = merged["calidad_metadatos"].fillna(0).astype(int)
        # Mantener el registro con mas metadatos cuando una URL coincide.
        merged = merged.sort_values("_quality_key", ascending=False).drop_duplicates(subset=["url"], keep="first")
        merged = merged.drop(columns=["_quality_key"])

    merged = aplicar_veredictos_revision(merged)
    carpeta = root / "outputs" / "integracion"
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")

    merged, no_residenciales = excluir_no_residenciales(merged)
    if not no_residenciales.empty:
        # Evidencia de la exclusion: las filas quedan en su propio CSV fechado
        # y solo desaparecen del maestro derivado; ninguna fuente original se
        # modifica.
        ruta_exclusion = carpeta / f"anuncios_no_residenciales_{marca}.csv"
        no_residenciales.to_csv(ruta_exclusion, index=False, encoding="utf-8-sig")
        motivos = {motivo: int(cantidad) for motivo, cantidad in no_residenciales["veredicto_revision"].value_counts().items()}
        print(
            f"Excluidos del dataset por no ser vivienda en venta: "
            f"{len(no_residenciales)} anuncios {motivos} -> {ruta_exclusion.name}"
        )

    merged, fuera_alcance = excluir_fuera_de_alcance(merged)
    if not fuera_alcance.empty:
        ruta_alcance = carpeta / f"anuncios_fuera_de_alcance_{marca}.csv"
        fuera_alcance.to_csv(ruta_alcance, index=False, encoding="utf-8-sig")
        motivos = {
            motivo: int(cantidad)
            for motivo, cantidad in fuera_alcance["motivo_alcance"].value_counts().items()
        }
        print(
            f"Excluidos del dataset por alcance (fuera de La Habana o no vivienda): "
            f"{len(fuera_alcance)} anuncios {motivos} -> {ruta_alcance.name}"
        )

    merged = aplicar_metadatos_revolico(merged)
    merged = aplicar_alcance_dudoso(merged)
    merged = aplicar_detalle_anuncios(merged)
    merged["precio_analisis"], merged["moneda_analisis"] = precios_analisis(merged)
    merged["origen_precio"] = "excluido"
    merged.loc[merged["precio_analisis"].notna(), "origen_precio"] = "campo_publicado"
    merged.loc[
        merged["precio_analisis"].notna() & merged["precio_reextraido"].notna(),
        "origen_precio",
    ] = "reextraccion_manual"
    # Ubicacion de analisis: municipio verificado en la pagina del anuncio primero,
    # campo publicado despues; vacio en el resto. No se imputa.
    merged["ubicacion_analisis"], merged["origen_ubicacion"] = ubicacion_analisis(merged)
    # Municipio homologado: solo los 15 municipios de La Habana; las zonas o
    # barrios que no son municipio quedan vacios (no se imputa).
    merged["municipio_homologado"] = merged["ubicacion_analisis"].map(homologar_municipio)
    # Habitaciones y banos de analisis: texto del anuncio primero, campo publicado
    # despues, slug del enlace al final; vacio si nada lo dice. No se imputa.
    (
        merged["habitaciones_analisis"],
        merged["banos_analisis"],
        merged["origen_habitaciones"],
        merged["origen_banos"],
    ) = detalle_analisis(merged)
    merged = merged.sort_values(["fuente", "id_local"], kind="stable").reset_index(drop=True)
    merged["id_maestro"] = [f"maestro_{i:06d}" for i in range(1, len(merged) + 1)]
    # Poner id_maestro primero para facilitar futuras uniones; las columnas de revision,
    # de precio de analisis y de metadatos de pagina se anaden al final porque son derivadas.
    columns = ["id_maestro"] + STANDARD_COLUMNS + [
        "veredicto_revision",
        "precio_reextraido",
        "moneda_reextraida",
        "evidencia_precio",
        "precio_analisis",
        "moneda_analisis",
        "origen_precio",
        "municipio_reextraido",
        "metodo_municipio",
        "fecha_reextraida",
        "estado_anuncio",
        "vendido",
        "evidencia_metadatos",
        "ubicacion_analisis",
        "origen_ubicacion",
        "municipio_homologado",
        "habitaciones_reextraido",
        "banos_reextraido",
        "habitaciones_slug",
        "banos_slug",
        "evidencia_detalle",
        "conflicto_detalle",
        "habitaciones_analisis",
        "banos_analisis",
        "origen_habitaciones",
        "origen_banos",
        "fecha_ultima_disponibilidad",
        "ventana_despublicacion",
        "justificacion_disponibilidad",
        "alcance_dudoso",
        "motivo_alcance_dudoso",
    ]
    return merged[columns]


def main():
    parser = argparse.ArgumentParser(description="Integracion no destructiva de fuentes inmobiliarias cubanas")
    parser.add_argument("--sin-dedup", action="store_true", help="No deduplicar por URL.")
    args = parser.parse_args()

    frame = integrar(dedup_by_url=not args.sin_dedup)
    out_dir = REPO_ROOT / "outputs" / "integracion"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Usar un nombre claro y reproducible con fecha+hora.
    output = out_dir / f"dataset_maestro_{stamp}.csv"
    frame.to_csv(output, index=False, encoding="utf-8-sig")

    summary = frame.groupby(["fuente", "moneda", "canal"], dropna=False).agg(
        anuncios=("id_maestro", "count"),
        precio_publicado=("precio_original", lambda s: int(pd.notna(s).sum())),
        precio_analisis=("precio_analisis", lambda s: int(pd.notna(s).sum())),
        precio_sospechoso=("precio_sospechoso", lambda s: int(s.sum())),
        habitaciones_publicadas=("habitaciones", lambda s: int(pd.notna(s).sum())),
        banos_publicados=("banos", lambda s: int(pd.notna(s).sum())),
    ).reset_index()
    summary_path = out_dir / f"resumen_integracion_{stamp}.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"Dataset maestro: {output}")
    print(f"Filas: {len(frame)}")
    print(f"Salida resumen: {summary_path}")
    print("\nPor fuente:")
    print(frame.groupby("fuente").size().to_string())
    print("\nMoneda:")
    print(frame["moneda"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
