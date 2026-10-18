#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auditoria read-only del dataset inmobiliario extraido de Revolico.

Este script solo LEE archivos CSV existentes y ESCRIBE un informe de auditoria.
No modifica, elimina ni sobrescribe CSV de datos originales ni derivados.
"""

from __future__ import annotations

import datetime
import hashlib
import platform
import re
import sys
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent
CSV_PRINCIPALES = [
    "enlaces_anuncios_revolico.csv",
    "anuncios_revolico_procesados.csv",
    "viviendas_revolico_candidatas.csv",
    "anuncios_revolico_revisar.csv",
    "anuncios_revolico_excluidos.csv",
    "datos_revolico_json.csv",
]
CSV_EJEMPLO = [
    "viviendas.csv",
    "viviendas_limpias.csv",
]


def hasha_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_csv(ruta: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(ruta)
    except Exception as exc:  # noqa: BLE001 - se reporta en el informe
        return None


def normalizar_titulo(serie: pd.Series) -> pd.Series:
    serie = serie.fillna("").astype(str).str.lower().str.strip()
    serie = serie.str.replace(r"\s+", " ", regex=True)
    serie = serie.str.replace(r"[^a-z0-9áéíóúñü\s]", "", regex=True)
    serie = serie.str.replace(r"\s+", " ", regex=True).str.strip()
    return serie


def contar_patron(serie: pd.Series, patron: str) -> int:
    return int(serie.fillna("").astype(str).str.contains(patron, regex=True, case=False, na=False).sum())


def fmt_tabla(filas: list[dict]) -> str:
    if not filas:
        return "_Sin datos._\n"
    columnas = list(filas[0].keys())
    salida = ["| " + " | ".join(columnas) + " |", "| " + " | ".join(["---"] * len(columnas)) + " |"]
    for fila in filas:
        salida.append("| " + " | ".join(str(fila[c]) for c in columnas) + " |")
    return "\n".join(salida) + "\n"


def principal() -> None:
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    salida_dir = RAIZ / "outputs" / "auditoria"
    salida_dir.mkdir(parents=True, exist_ok=True)
    reporte = salida_dir / f"auditoria_revolico_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    todas = CSV_PRINCIPALES + CSV_EJEMPLO
    disponibles = [nombre for nombre in todas if (RAIZ / nombre).exists()]
    faltantes = [nombre for nombre in todas if not (RAIZ / nombre).exists()]

    dataframes = {}
    for nombre in disponibles:
        dataframes[nombre] = leer_csv(RAIZ / nombre)

    lineas: list[str] = []
    lineas.append("# Auditoria read-only: dataset inmobiliario Revolico")
    lineas.append("")
    lineas.append(f"- Fecha y hora: `{ahora}`")
    lineas.append(f"- Raiz del proyecto: `{RAIZ}`")
    lineas.append(f"- Python: `{sys.version.split()[0]}`")
    lineas.append(f"- pandas: `{pd.__version__}`")
    lineas.append("- Modo: solo lectura. No se modificaron CSV de entrada.")
    lineas.append("")
    lineas.append("## 1. Archivos auditados")
    lineas.append("")
    lineas.append("SHA-256 calculado durante la auditoria (no implica cambio de archivo).")
    lineas.append("")
    filas_archivos = []
    for nombre in disponibles:
        ruta = RAIZ / nombre
        df = dataframes.get(nombre)
        filas_archivos.append({
            "archivo": nombre,
            "bytes": ruta.stat().st_size,
            "filas": len(df) if df is not None else "ERROR",
            "columnas": len(df.columns) if df is not None else "ERROR",
            "sha256": hasha_archivo(ruta),
        })
    lineas.append(fmt_tabla(filas_archivos))
    if faltantes:
        lineas.append("Archivos esperados no encontrados: " + ", ".join(f"`{x}`" for x in faltantes) + ".")
        lineas.append("")

    lineas.append("## 2. Valores ausentes")
    lineas.append("")
    hubo_ausencias = False
    for nombre in disponibles:
        df = dataframes.get(nombre)
        if df is None:
            lineas.append(f"### {nombre}")
            lineas.append("")
            lineas.append("No se pudo leer el archivo.")
            lineas.append("")
            continue
        lineas.append(f"### {nombre} ({len(df)} filas)")
        lineas.append("")
        nulos = df.isna().sum()
        total = len(df)
        filas_nulos = []
        for columna in df.columns:
            cantidad = int(nulos[columna])
            porcentaje = (cantidad / total * 100) if total else 0.0
            if cantidad > 0:
                hubo_ausencias = True
            filas_nulos.append({
                "columna": columna,
                "ausentes": cantidad,
                "porcentaje": f"{porcentaje:.2f}%",
            })
        lineas.append(fmt_tabla(filas_nulos))
    if not hubo_ausencias:
        lineas.append("No se detectaron valores ausentes en los archivos leidos.")
        lineas.append("")

    lineas.append("## 3. Duplicados exactos y por URL/titulo")
    lineas.append("")
    for nombre in disponibles:
        df = dataframes.get(nombre)
        if df is None:
            continue
        lineas.append(f"### {nombre}")
        lineas.append("")
        lineas.append(f"- Filas totales: {len(df)}")
        lineas.append(f"- Filas exactamente duplicadas (toda la fila): {int(df.duplicated().sum())}")
        if "url" in df.columns:
            lineas.append(f"- URLs duplicadas: {int(df['url'].duplicated().sum())}")
        if "titulo" in df.columns:
            lineas.append(f"- Titulos exactamente duplicados: {int(df['titulo'].duplicated().sum())}")
            normal = normalizar_titulo(df["titulo"])
            lineas.append(f"- Titulos duplicados tras normalizacion: {int(normal.duplicated().sum())}")
            # Muestra de titulos normalizados repetidos
            repetidos = normal[normal.duplicated(keep=False)].value_counts().head(10)
            if not repetidos.empty:
                lineas.append("")
                lineas.append("Titulos normalizados mas repetidos (hasta 10):")
                lineas.append("")
                for texto, cantidad in repetidos.items():
                    lineas.append(f"- `{texto}`: {cantidad}")
        lineas.append("")

    lineas.append("## 4. Títulos sin tipo de propiedad")
    lineas.append("")
    if "anuncios_revolico_procesados.csv" in dataframes and dataframes["anuncios_revolico_procesados.csv"] is not None:
        df = dataframes["anuncios_revolico_procesados.csv"]
        titulo_norm = df["titulo"].fillna("").astype(str).str.lower()
        patron_propiedad = re.compile(r"casa|apartamento|apto|apart|departamento|depto", re.IGNORECASE)
        sin_tipo = ~titulo_norm.str.contains(patron_propiedad, regex=True, na=False)
        lineas.append(f"- Total de filas procesadas: {len(df)}")
        lineas.append(f"- Titulos sin palabras tipo propiedad: {int(sin_tipo.sum())}")
        lineas.append(f"- Titulos con palabras tipo propiedad: {int((~sin_tipo).sum())}")
        if "sirve_proyecto" in df.columns:
            lineas.append("")
            lineas.append("Distribucion de `sirve_proyecto`:")
            lineas.append("")
            for categoria, cantidad in df["sirve_proyecto"].value_counts(dropna=False).items():
                lineas.append(f"- `{categoria}`: {cantidad}")
        lineas.append("")
        lineas.append("Ejemplos de titulos sin tipo de propiedad (hasta 15):")
        lineas.append("")
        for titulo in df.loc[sin_tipo, "titulo"].head(15):
            lineas.append(f"- `{str(titulo)}`")
        lineas.append("")
    else:
        lineas.append("No se encontro `anuncios_revolico_procesados.csv`.")

    lineas.append("## 5. Precios sospechosos y validacion basica")
    lineas.append("")
    if "anuncios_revolico_procesados.csv" in dataframes and dataframes["anuncios_revolico_procesados.csv"] is not None:
        df = dataframes["anuncios_revolico_procesados.csv"]
        total = len(df)
        precio = pd.to_numeric(df["precio"], errors="coerce")
        moneda = df["moneda"]
        lineas.append(f"- Filas totales: {total}")
        lineas.append(f"- Precio no disponible: {int(precio.isna().sum())}")
        lineas.append(f"- Moneda no disponible: {int(moneda.isna().sum())}")
        lineas.append(f"- Precio disponible pero moneda ausente: {int(((precio.notna()) & (moneda.isna())).sum())}")
        lineas.append(f"- Precio <= 0: {int((precio <= 0).sum())}")
        lineas.append(f"- Precio < 100: {int((precio < 100).sum())}")
        lineas.append(f"- Precio < 1000: {int((precio < 1000).sum())}")
        lineas.append(f"- Precio > 100000: {int((precio > 100000).sum())}")
        lineas.append(f"- Precio igual a 1: {int((precio == 1).sum())}")
        titulo_digits = df["titulo"].fillna("").astype(str).str.match(r"^\s*\d{7,}")
        lineas.append(f"- Titulos que comienzan con 7 o mas digitos (posible telefono/monto no monetario): {int(titulo_digits.sum())}")
        lineas.append("")
        lineas.append("Distribucion de `moneda`:")
        lineas.append("")
        for valor, cantidad in moneda.value_counts(dropna=False).items():
            etiqueta = "NA" if pd.isna(valor) else str(valor)
            lineas.append(f"- `{etiqueta}`: {cantidad}")
        lineas.append("")
        if precio.notna().any():
            lineas.append("Resumen numerico de precio:")
            lineas.append("")
            lineas.append("```text")
            lineas.append(precio.describe().to_string())
            lineas.append("```")
            lineas.append("")
        lineas.append("10 precios mas altos:")
        lineas.append("")
        for _, fila in df.assign(_precio=precio).sort_values("_precio", ascending=False).head(10).iterrows():
            lineas.append(f"- {fila['precio']} {fila['moneda']} | `{fila['titulo']}`")
        lineas.append("")
        lineas.append("10 precios mas bajos:")
        lineas.append("")
        for _, fila in df.assign(_precio=precio).sort_values("_precio", ascending=True).head(10).iterrows():
            lineas.append(f"- {fila['precio']} {fila['moneda']} | `{fila['titulo']}`")
        lineas.append("")
    else:
        lineas.append("No se encontro `anuncios_revolico_procesados.csv`.")

    lineas.append("## 6. Cobertura territorial y de tamaño")
    lineas.append("")
    if "anuncios_revolico_procesados.csv" in dataframes and dataframes["anuncios_revolico_procesados.csv"] is not None:
        df = dataframes["anuncios_revolico_procesados.csv"]
        total = len(df)
        if "municipio" in df.columns:
            lineas.append(f"- Municipio no disponible: {int(df['municipio'].isna().sum())} ({df['municipio'].isna().mean() * 100:.2f}%)")
            lineas.append("")
            lineas.append("Municipios mas frecuentes:")
            lineas.append("")
            for municipio, cantidad in df["municipio"].value_counts(dropna=False).head(20).items():
                etiqueta = "NA" if pd.isna(municipio) else str(municipio)
                lineas.append(f"- `{etiqueta}`: {cantidad}")
            lineas.append("")
        if "habitaciones" in df.columns:
            habitaciones = pd.to_numeric(df["habitaciones"], errors="coerce")
            lineas.append(f"- Habitaciones no disponibles: {int(habitaciones.isna().sum())} ({habitaciones.isna().mean() * 100:.2f}%)")
            lineas.append("")
            lineas.append("Distribucion de habitaciones (solo disponibles):")
            lineas.append("")
            for valor, cantidad in habitaciones.value_counts(dropna=True).sort_index().items():
                lineas.append(f"- `{valor:g}`: {cantidad}")
            lineas.append("")
        # Candidatos tambien
    if "viviendas_revolico_candidatas.csv" in dataframes and dataframes["viviendas_revolico_candidatas.csv"] is not None:
        c = dataframes["viviendas_revolico_candidatas.csv"]
        lineas.append("Candidatas (sirve_proyecto == SI):")
        lineas.append("")
        lineas.append(f"- Filas: {len(c)}")
        lineas.append(f"- Municipio ausente: {int(c['municipio'].isna().sum())}")
        lineas.append(f"- Habitaciones ausentes: {int(c['habitaciones'].isna().sum())}")
        lineas.append(f"- Precio ausente: {int(c['precio'].isna().sum())}")
        lineas.append("")

    lineas.append("## 7. Variables potencialmente extraibles desde `texto_tarjeta`")
    lineas.append("")
    lineas.append("IMPORTANTE: en `enlaces_anuncios_revolico.csv`, `texto_tarjeta` fue extraido tomando un contenedor compartido, por lo que una tarjeta puede mezclar varios anuncios. Los conteos siguientes son orientativos para rediseñar la extraccion; no son validos como features finales sin verificacion individual.")
    lineas.append("")
    if "enlaces_anuncios_revolico.csv" in dataframes and dataframes["enlaces_anuncios_revolico.csv"] is not None:
        enlaces = dataframes["enlaces_anuncios_revolico.csv"]
        texto = enlaces["texto_tarjeta"]
        patrones = {
            "m2/metros cuadrados": r"\bm2\b|\bm²\b|m2\.|metros cuadrados|metros²",
            "baños/banos": r"ba[ñn]os?|bano",
            "garaje/parking": r"garaje|parking|parqueo",
            "terraza": r"terraza",
            "balcón/balcon": r"balc[oó]n",
            "patio": r"patio",
            "piscina": r"piscina",
            "planta": r"planta",
            "placa": r"placa",
            "portal": r"portal",
            "cuartos/habitaciones": r"cuartos?|habitaciones?",
        }
        filas_patrones = []
        for nombre_patron, patron in patrones.items():
            filas_patrones.append({
                "patron": nombre_patron,
                "filas_con_match": contar_patron(texto, patron),
                "porcentaje": f"{contar_patron(texto, patron) / len(enlaces) * 100:.2f}%",
            })
        lineas.append(fmt_tabla(filas_patrones))
        lineas.append(f"Longitud de `texto_tarjeta`: media {texto.str.len().mean():.1f}, min {texto.str.len().min()}, max {texto.str.len().max()}.")
        lineas.append(f"Tarjetas con 10 o mas enlaces internos de anuncio: no calculado row-wise en CSV. Ver scripts de exploracion en futuras etapas.")
        lineas.append("")
    else:
        lineas.append("No se encontro `enlaces_anuncios_revolico.csv`.")

    lineas.append("## 8. Comparacion con Cubisima (sin integracion)")
    lineas.append("")
    lineas.append("El repositorio contiene archivos untracked de Cubisima (`scraper_cubisima.py`, `viviendas_cubisima.csv`, etc.). No se han integrado al proyecto principal en esta etapa. Solo se reporta su existencia para evitar confusion en la trazabilidad.")
    if "viviendas_cubisima.csv" in dataframes and dataframes["viviendas_cubisima.csv"] is not None:
        cub = dataframes["viviendas_cubisima.csv"]
        lineas.append("")
        lineas.append(f"- `viviendas_cubisima.csv`: {len(cub)} filas x {len(cub.columns)} columnas (archivo untracked, no integrado).")
    lineas.append("")

    lineas.append("## 9. Limitaciones y datos no verificados")
    lineas.append("")
    lineas.append("- El corpus se basa en 8 paginas HTML descargadas manualmente de Revolico; no se verifico muestreo probabilistico ni cobertura completa del sitio.")
    lineas.append("- Los precios provienen del titulo y pueden incluir telefonos u otros numeros; aun no se habian verificado contra el texto individual del anuncio.")
    lineas.append("- `municipio` y `habitaciones` presentan ausencias altas porque solo se extrajeron patrones del titulo.")
    lineas.append("- `texto_tarjeta` esta contaminado por contenedores compartidos; sus conteos son orientativos, no features validados.")
    lineas.append("- `datos_revolico_json.csv` no corresponde a viviendas exclusivamente y no fue usado como fuente principal.")
    lineas.append("- No se verificaron las paginas individuales de anuncios, por lo que no se confirmo la disponibilidad de baños, m2, planta, garaje o fecha.")
    lineas.append("- No se ejecuto limpieza, deduplicacion robusta ni analisis estadistico/visual mas alla de conteos.")
    lineas.append("- No se comprobo correspondencia entre CSV y commit concreto; las paginas HTML estan ignoradas por Git.")
    lineas.append("- No se integraron archivos de Cubisima en esta auditoria.")
    lineas.append("")

    lineas.append("## 10. Conclusion")
    lineas.append("")
    lineas.append("La base actual tiene un flujo funcional, pero la calidad para una investigacion rigurosa depende de mejorar la extraccion individual por anuncio, validar precios y reducir ausencias de municipio/habitaciones. Antes de continuar, se recomienda revisar este informe y aprobar las modificaciones no destructivas de la siguiente etapa.")
    lineas.append("")

    reporte.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Reporte generado: {reporte}")


if __name__ == "__main__":
    principal()
