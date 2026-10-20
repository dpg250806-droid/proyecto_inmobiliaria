#!/usr/bin/env python3
"""Genera la lista de precios pendientes sobre el maestro vigente.

Filtra los anuncios sin `precio_analisis` del maestro actual, les asigna el
motivo registrado en `veredicto_revision` y la accion sugerida, y escribe la
lista en `outputs/validacion/` (CSV y Markdown) para revision manual.

No imputa ningun precio y no modifica el maestro.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
VALIDACION_DIR = ROOT / "outputs" / "validacion"

MOTIVOS = {
    "sin_precio_en_texto": "El texto no menciona un precio verificable",
    "solo_coincide_con_publicado": "Solo hay precio publicado, sin verificacion en el texto",
    "no_verificable": "No se pudo verificar el precio",
    "anuncio_no_disponible": "Anuncio no disponible al consultar",
    "cup_requiere_validacion": "Precio en CUP: requiere validacion",
    "despublicado": "Anuncio despublicado",
    "ambiguo": "Precio ambiguo",
    "error": "Error de consulta",
    "moneda_ambigua": "Moneda ambigua",
    "valor_improbable": "Valor improbable",
}

ACCIONES = {
    "sin_precio_en_texto": "Revisar texto y URL; si no hay precio, dejar como ausente",
    "solo_coincide_con_publicado": "Confirmar si el precio publicado es el precio de venta",
    "no_verificable": "Revisar manualmente; no imputar",
    "anuncio_no_disponible": "No accionable por ahora; conservar marca",
    "cup_requiere_validacion": "Validar CUP y moneda antes de usar",
    "despublicado": "No accionable; conservar marca",
    "ambiguo": "Leer descripcion completa y decidir",
    "error": "Repetir consulta si hay red",
    "moneda_ambigua": "Determinar moneda antes de usar",
    "valor_improbable": "Revisar precio y unidad",
}

FECHA_REVISION = "2026-10-19"


def main() -> None:
    maestro_path = sorted(MASTER_DIR.glob("dataset_maestro_*.csv"))[-1]
    maestro = pd.read_csv(maestro_path, dtype=str).fillna("")
    maestro["precio_num"] = pd.to_numeric(maestro["precio_analisis"], errors="coerce")
    pendientes = maestro[maestro["precio_num"].isna()].copy()

    anteriores = sorted(VALIDACION_DIR.glob("precios_pendientes_*.csv"))
    observaciones: dict[str, str] = {}
    if anteriores:
        previo = pd.read_csv(anteriores[-1], dtype=str).fillna("")
        if "url" in previo.columns and "observacion" in previo.columns:
            observaciones = previo.set_index("url")["observacion"].to_dict()

    filas = []
    for _, fila in pendientes.sort_values(["fuente", "veredicto_revision", "id_local"]).iterrows():
        veredicto = fila["veredicto_revision"] or "(vacio)"
        filas.append(
            {
                "fuente": fila["fuente"],
                "id_local": fila["id_local"],
                "url": fila["url"],
                "titulo": fila["titulo"],
                "veredicto": veredicto,
                "motivo": MOTIVOS.get(veredicto, "Requiere revision"),
                "accion_sugerida": ACCIONES.get(veredicto, "Revisar manualmente"),
                "precio_publicado": fila["precio_original"],
                "moneda_publicada": fila["moneda"],
                "observacion": observaciones.get(fila["url"], fila["observacion"]),
                "fecha_revision": FECHA_REVISION,
                "maestro_origen": maestro_path.name,
            }
        )

    salida = pd.DataFrame(filas)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    VALIDACION_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = VALIDACION_DIR / f"precios_pendientes_actualizado_{marca}.csv"
    md_path = VALIDACION_DIR / f"precios_pendientes_actualizado_{marca}.md"
    salida.to_csv(csv_path, index=False, encoding="utf-8")

    lineas = [
        "# Precios pendientes de revision (maestro actual)",
        "",
        f"- Maestro: `{maestro_path.name}`",
        f"- Anuncios sin precio de analisis: **{len(salida)}**",
        "- No se imputa ningun valor; esta lista es para revision manual.",
        "",
        "## Conteo por motivo",
        "",
        salida["veredicto"]
        .value_counts()
        .rename_axis("veredicto")
        .reset_index(name="anuncios")
        .to_markdown(index=False),
        "",
        "## Detalle",
        "",
        salida[
            [
                "fuente",
                "id_local",
                "titulo",
                "veredicto",
                "motivo",
                "accion_sugerida",
                "precio_publicado",
                "moneda_publicada",
                "url",
            ]
        ].to_markdown(index=False),
    ]
    md_path.write_text("\n".join(lineas), encoding="utf-8")
    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(f"Filas: {len(salida)}")
    print(salida["veredicto"].value_counts().to_string())


if __name__ == "__main__":
    main()
