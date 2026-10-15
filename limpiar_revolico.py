#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpieza no destructiva del dataset Revolico.

Lee unicamente los CSV existentes y escribe un nuevo dataset derivado en
outputs/limpieza/. No modifica ni sobrescribe los archivos de entrada.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "anuncios_revolico_procesados.csv"


def normalizar_texto(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor)
    texto = unicodedata.normalize("NFKC", texto).strip().lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def canonicalizar_municipio(valor: object) -> str | None:
    if pd.isna(valor):
        return None
    clave = normalizar_texto(valor)
    mapa = {
        "arroyo naranjo": "Arroyo Naranjo",
        "boyeros": "Boyeros",
        "centro habana": "Centro Habana",
        "cerro": "Cerro",
        "cotorro": "Cotorro",
        "diez de octubre": "Diez de Octubre",
        "10 de octubre": "Diez de Octubre",
        "guanabacoa": "Guanabacoa",
        "habana del este": "Habana del Este",
        "habana vieja": "Habana Vieja",
        "la lisa": "La Lisa",
        "marianao": "Marianao",
        "playa": "Playa",
        "plaza de la revolucion": "Plaza de la RevoluciÃ³n",
        "plaza de la revoluciÃ³n": "Plaza de la RevoluciÃ³n",
        "regla": "Regla",
        "san miguel del padron": "San Miguel del PadrÃ³n",
        "san miguel del padrÃ³n": "San Miguel del PadrÃ³n",
    }
    return mapa.get(clave, str(valor).strip())


def extraer_entero(texto: str, patron: str) -> float | None:
    match = re.search(patron, texto, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def principal() -> None:
    if not ENTRADA.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {ENTRADA}")

    df = pd.read_csv(ENTRADA).copy()
    filas_iniciales = len(df)

    df["titulo_normalizado"] = df["titulo"].map(normalizar_texto)
    df["municipio_normalizado"] = df["municipio"].map(canonicalizar_municipio)

    # Clasificacion de tipo a partir del titulo.
    titulo = df["titulo_normalizado"]
    df["tipo_vivienda"] = "no_clasificado"
    df.loc[titulo.str.contains(r"apart|apto", regex=True, na=False), "tipo_vivienda"] = "apartamento"
    df.loc[titulo.str.contains(r"\bcasa\b", regex=True, na=False), "tipo_vivienda"] = "casa"
    df.loc[titulo.str.contains("penthouse", regex=False, na=False), "tipo_vivienda"] = "penthouse"

    # Variables solo cuando aparecen explicitamente en el titulo.
    df["banos_titulo"] = df["titulo_normalizado"].map(lambda x: extraer_entero(x, r"(\d+)\s*ba[ñn]os?"))
    df["m2_titulo"] = df["titulo_normalizado"].map(lambda x: extraer_entero(x, r"(\d+)\s*(?:m2|mÂ²|metros?)"))
    df["habitaciones"] = pd.to_numeric(df["habitaciones"], errors="coerce")

    # Flags de calidad, sin borrar automaticamente.
    df["precio_sospechoso_bajo"] = pd.to_numeric(df["precio"], errors="coerce").lt(100)
    df["precio_sospechoso_alto"] = pd.to_numeric(df["precio"], errors="coerce").gt(100000)
    df["precio_disponible"] = pd.to_numeric(df["precio"], errors="coerce").notna() & df["moneda"].notna()
    df["titulo_comienza_con_7_o_mas_digitos"] = df["titulo"].fillna("").astype(str).str.match(r"^\s*\d{7,}")

    claves_exclusion = [
        "busco alquiler",
        "busco casa",
        "busco apartamento",
        "busco apto",
        "compro",
        "se busca",
        "alquilo",
        "se alquila",
        "vendo terreno",
        "se vende terreno",
        "terreno",
        "solar",
        "almacen",
        "local",
        "finca",
        "oficina",
        "negocio",
        "por dias",
        "habitacion",
    ]
    patron_exclusion = "|".join(re.escape(clave) for clave in claves_exclusion)
    df["excluido_sugerido"] = df["titulo_normalizado"].str.contains(patron_exclusion, regex=True, na=False)

    df["motivo_exclusion"] = ""
    for clave in claves_exclusion:
        mascara = df["motivo_exclusion"].eq("") & df["titulo_normalizado"].str.contains(re.escape(clave), regex=True, na=False)
        df.loc[mascara, "motivo_exclusion"] = clave

    # Deduplicacion conservadora: mismo titulo normalizado + misma moneda + mismo precio.
    df["clave_duplicado"] = (
        df["titulo_normalizado"]
        + " | "
        + df["moneda"].fillna("NA").astype(str).str.upper()
        + " | "
        + df["precio"].fillna(-1).astype(str)
    )
    mascara_duplicado = df.duplicated(subset=["clave_duplicado"], keep="first")
    df["duplicado_conservador"] = mascara_duplicado

    # Base analitica sugerida: excluidos no sugeridos, con precio y moneda disponibles.
    mascara_base = (~df["excluido_sugerido"]) & df["precio_disponible"]
    base = df.loc[mascara_base & ~mascara_duplicado].copy()

    # Salidas no destructivas.
    salida_dir = RAIZ / "outputs" / "limpieza"
    salida_dir.mkdir(parents=True, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_dataset = salida_dir / f"viviendas_revolico_variables_{sello}.csv"
    ruta_resumen = salida_dir / f"resumen_limpieza_{sello}.md"

    columnas_salida = [
        "titulo",
        "titulo_normalizado",
        "url",
        "pagina_origen",
        "precio",
        "moneda",
        "sirve_proyecto",
        "tipo_vivienda",
        "municipio",
        "municipio_normalizado",
        "habitaciones",
        "banos_titulo",
        "m2_titulo",
        "precio_sospechoso_bajo",
        "precio_sospechoso_alto",
        "precio_disponible",
        "titulo_comienza_con_7_o_mas_digitos",
        "excluido_sugerido",
        "motivo_exclusion",
        "duplicado_conservador",
    ]
    base[columnas_salida].to_csv(ruta_dataset, index=False, encoding="utf-8-sig")

    lineas = []
    lineas.append("# Resumen de limpieza no destructiva (Revolico)")
    lineas.append("")
    lineas.append(f"- Fecha y hora: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lineas.append(f"- Entrada: `{ENTRADA.name}` (no modificada)")
    lineas.append(f"- Filas iniciales: {filas_iniciales}")
    lineas.append(f"- Excluidos sugeridos: {int(df['excluido_sugerido'].sum())}")
    lineas.append(f"- Sin precio o moneda: {int((~df['precio_disponible']).sum())}")
    lineas.append(f"- Duplicados conservadores removidos: {int(mascara_duplicado.sum())}")
    lineas.append(f"- Filas en base analitica sugerida: {len(base)}")
    lineas.append("")
    lineas.append("## Tipos de vivienda detectados")
    lineas.append("")
    for tipo, cantidad in df["tipo_vivienda"].value_counts(dropna=False).items():
        lineas.append(f"- `{tipo}`: {cantidad}")
    lineas.append("")
    lineas.append("## Municipios normalizados mas frecuentes")
    lineas.append("")
    for municipio, cantidad in df["municipio_normalizado"].value_counts(dropna=False).head(20).items():
        etiqueta = "NA" if pd.isna(municipio) else str(municipio)
        lineas.append(f"- `{etiqueta}`: {cantidad}")
    lineas.append("")
    lineas.append("## Motivos de exclusion sugerida")
    lineas.append("")
    motivos = df.loc[df["excluido_sugerido"], "motivo_exclusion"].value_counts()
    if motivos.empty:
        lineas.append("No se detectaron exclusiones sugeridas.")
    else:
        for motivo, cantidad in motivos.items():
            lineas.append(f"- `{motivo}`: {cantidad}")
    lineas.append("")
    lineas.append("## Variables adicionales encontradas en titulo")
    lineas.append("")
    lineas.append(f"- Habitaciones disponibles: {int(df['habitaciones'].notna().sum())}")
    lineas.append(f"- BaÃ±os mencionados en titulo: {int(df['banos_titulo'].notna().sum())}")
    lineas.append(f"- Metros cuadrados mencionados en titulo: {int(df['m2_titulo'].notna().sum())}")
    lineas.append("")
    lineas.append("## Precios sospechosos")
    lineas.append("")
    lineas.append(f"- Precio bajo (< 100): {int(df['precio_sospechoso_bajo'].sum())}")
    lineas.append(f"- Precio alto (> 100000): {int(df['precio_sospechoso_alto'].sum())}")
    lineas.append(f"- Titulo comienza con 7 o mas digitos: {int(df['titulo_comienza_con_7_o_mas_digitos'].sum())}")
    lineas.append("")
    lineas.append("Dataset derivado guardado en `outputs/limpieza/`.")
    lineas.append("")

    ruta_resumen.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Dataset derivado: {ruta_dataset}")
    print(f"Resumen: {ruta_resumen}")
    print(f"Filas iniciales: {filas_iniciales}; base sugerida: {len(base)}")


if __name__ == "__main__":
    principal()
