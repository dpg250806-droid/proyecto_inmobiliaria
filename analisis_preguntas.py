#!/usr/bin/env python3
"""Genera respuestas tabuladas a las preguntas de investigacion."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

from precio_moneda import detalle_analisis, precios_analisis
from procesar_entrevistas import plain_text

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
CONV_DIR = ROOT / "outputs" / "conversiones"
OUT = ROOT / "outputs" / "preguntas"
ENTREVISTAS_DIR = ROOT / "outputs" / "entrevistas"


def latest(directory: Path, pattern: str) -> Path:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(directory / pattern)
    return files[-1]


def clean_boolean(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "si", "sí"])


def rank_associations(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = frame.copy()
    if "precio_analisis" not in frame.columns or "moneda_analisis" not in frame.columns:
        # Frames de prueba o maestros antiguos: derivar el precio de analisis aqui.
        frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    # Habitaciones y banos de analisis (texto del anuncio, campo publicado o slug);
    # `detalle_analisis` cae al campo publicado si el frame no trae reextraccion.
    (
        frame["habitaciones_analisis"],
        frame["banos_analisis"],
        _,
        _,
    ) = detalle_analisis(frame)
    # La superficie (m2) queda fuera del analisis: ninguna fuente la publica al
    # 100% (Revolico y Cubisima 0%, HogarEnCuba ~5%), por lo que solo se reporta
    # su cobertura como hallazgo comparativo, nunca en estadisticas de precios.
    for (source, currency), group in frame.groupby(["fuente", "moneda_analisis"]):
        for campo, etiqueta in (
            ("habitaciones_analisis", "habitaciones"),
            ("banos_analisis", "banos"),
        ):
            if campo not in group:
                continue
            pair = group[["precio_analisis", campo]].dropna()
            if len(pair) < 5 or pair[campo].nunique() < 2 or pair["precio_analisis"].nunique() < 2:
                continue
            coefficient = pair["precio_analisis"].rank().corr(pair[campo].rank())
            rows.append({
                "fuente": source,
                "moneda": currency,
                "variable": etiqueta,
                "n": len(pair),
                "spearman_rho": round(float(coefficient), 3),
            })
    return pd.DataFrame(rows)


def seccion_entrevistas() -> list[str]:
    """Bloque de evidencia cualitativa a partir de las entrevistas ya procesadas.

    Lee el CSV codificado mas reciente de `outputs/entrevistas/` y reporta solo
    frecuencias de palabras clave y conteos verificables; la lectura interpretativa
    se hace a mano en el informe, con las respuestas literales auditables en
    `resumen_entrevistas_*.md`. No atribuye causalidad.
    """
    try:
        coded_path = latest(ENTREVISTAS_DIR, "entrevistas_codificadas_*.csv")
    except FileNotFoundError:
        return [
            "No hay entrevistas procesadas en `outputs/entrevistas/`; para incorporarlas ejecute "
            "`procesar_entrevistas.py --csv <export>`.",
        ]
    coded = pd.read_csv(coded_path, dtype=str).fillna("")
    n = len(coded)
    lines = [
        f"Entrevistas procesadas: {n} (`{coded_path.name}`), anonimas y codificadas como "
        f"E01..E{n:02d} por `procesar_entrevistas.py`."
    ]
    fechas = pd.to_datetime(coded.get("fecha_respuesta", pd.Series(dtype=str)), errors="coerce")
    if fechas.notna().any():
        lines.append(f"- Fechas de respuesta: del {fechas.min().date()} al {fechas.max().date()}.")
    code_cols = [c for c in coded.columns if c.startswith("C") and c[1].isdigit()]
    if code_cols:
        frec = [(c, int(pd.to_numeric(coded[c], errors="coerce").fillna(0).sum())) for c in code_cols]
        lines.append(
            "- Presencia de temas en el texto de las respuestas (heuristica de palabras clave, "
            "acento-insensible; ver `data_dictionary.md`): "
            + "; ".join(f"{c} = {v}/{n}" for c, v in frec)
            + "."
        )
    if "factor_dominante" in coded.columns:
        textos = [plain_text(t) for t in coded["factor_dominante"]]
        menciones = [
            ("migracion", sum("migra" in t for t in textos)),
            ("crisis economica", sum("crisis" in t for t in textos)),
            ("tasas o divisas", sum(("tasa" in t) or ("divisa" in t) for t in textos)),
        ]
        lines.append(
            "- En la pregunta del factor dominante (varias respuestas nombran mas de un factor): "
            + "; ".join(f"{k} {v}/{n}" for k, v in menciones)
            + ". Las respuestas literales estan en `outputs/entrevistas/resumen_entrevistas_*.md`."
        )
    if "municipio" in coded.columns:
        mun = coded["municipio"].replace({"": pd.NA}).dropna().value_counts()
        if len(mun):
            lines.append(
                "- Municipios de las viviendas de mayor conocimiento: "
                + "; ".join(f"{k} ({v})" for k, v in mun.items())
                + "."
            )
    lines.append(
        "- Cruce con los datos de anuncios (asociacion, no causalidad): las percepciones sobre la "
        "evolucion de precios desde 2020 no son verificables ni refutables con una muestra "
        "transversal de anuncios publicados sobre todo en 2026; se presentan como evidencia "
        "cualitativa y se contrastan con medianas y agrupamientos, sin estimar efectos."
    )
    return lines


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master_path = latest(MASTER_DIR, "dataset_maestro_*.csv")
    conversion_path = latest(CONV_DIR, "dataset_maestro_conversion_*.csv")
    master = pd.read_csv(master_path, dtype=str)
    conversion = pd.read_csv(conversion_path, dtype=str)

    master["precio_original"] = pd.to_numeric(master["precio_original"], errors="coerce")
    # Campos publicados: se conservan solo para la tabla de cobertura.
    master["habitaciones"] = pd.to_numeric(master["habitaciones"], errors="coerce")
    master["banos"] = pd.to_numeric(master["banos"], errors="coerce")
    # La superficie (m2) queda fuera del analisis: ninguna fuente la publica al 100%.
    master["moneda"] = master["moneda"].fillna("").astype(str).str.strip().str.upper().replace("", "SIN_MONEDA")
    master["precio_sospechoso"] = clean_boolean(master["precio_sospechoso"])
    # Precio de analisis: prefiere la reextraccion manual y excluye campos sospechosos.
    master["precio_analisis"], master["moneda_analisis"] = precios_analisis(master)
    master["moneda_analisis"] = master["moneda_analisis"].replace("", "SIN_MONEDA")
    conversion["precio_usd_informal"] = pd.to_numeric(conversion["precio_usd_informal"], errors="coerce")
    conversion["precio_usd_formal"] = pd.to_numeric(conversion["precio_usd_formal"], errors="coerce")
    conversion["moneda"] = conversion["moneda"].fillna("").astype(str).str.strip().str.upper().replace("", "SIN_MONEDA")
    # Habitaciones y banos de analisis (texto del anuncio, campo publicado o slug);
    # en maestros antiguos sin esas columnas, `detalle_analisis` cae al publicado.
    (
        master["habitaciones_analisis"],
        master["banos_analisis"],
        _,
        _,
    ) = detalle_analisis(master)
    price_data = master[
        master["precio_analisis"].notna()
        & master["moneda_analisis"].ne("SIN_MONEDA")
    ].copy()

    lines = []
    lines.append("# Analisis exploratorio y linea narrativa (no es el informe final)")
    lines.append("")
    lines.append(f"Dataset maestro: `{master_path.name}`")
    lines.append(f"Conversiones: `{conversion_path.name}`")
    lines.append(f"Filas en maestro: {len(master)}; precios utilizables (mejor precio disponible con moneda): {len(price_data)}.")
    lines.append("")
    lines.append("## Evidencia y alcance de la muestra")
    lines.append("")
    coverage = master.groupby("fuente").agg(
        anuncios=("id_maestro", "count"),
        precio_disponible=("precio_original", "count"),
        ubicacion_disponible=("ubicacion_raw", "count"),
        ubicacion_analisis=("ubicacion_analisis", lambda s: int(s.fillna("").astype(str).str.strip().ne("").sum())),
        habitaciones_publicadas=("habitaciones", "count"),
        habitaciones_analisis=("habitaciones_analisis", "count"),
        banos_publicados=("banos", "count"),
        banos_analisis=("banos_analisis", "count"),
        fecha_publicacion=("fecha_publicacion", "count"),
        fecha_reextraida=("fecha_reextraida", lambda s: int(s.fillna("").astype(str).str.strip().ne("").sum())),
    ).reset_index()
    lines.append(coverage.to_markdown(index=False))
    lines.append("")
    lines.append("Distribucion de anuncios por moneda publicada en el campo de precio:")
    lines.append("")
    currency_counts = master.groupby(["fuente", "moneda"], dropna=False).size().rename("anuncios").reset_index()
    lines.append(currency_counts.to_markdown(index=False))
    lines.append("")
    lines.append(
        "La unidad observada es un anuncio, no una transaccion cerrada. Los precios sospechosos, "
        "sin moneda o sin importe se excluyen de estadisticas de precios; no se imputan. "
        "Donde la revision manual verifico un precio en la descripcion o en el titulo, ese valor "
        "se usa como `precio_analisis` y el campo publicado se conserva sin corregir."
    )
    lines.append("")

    lines.append("## 1. Precio central por fuente y moneda")
    stats = price_data.groupby(["fuente", "moneda_analisis"])["precio_analisis"].agg(["count", "median", "mean", "min", "max"]).reset_index()
    lines.append(stats.to_markdown(index=False))
    lines.append("")

    lines.append("## 2. Precio por municipio/zona (top 10 por moneda, cobertura suficiente)")
    muni = price_data[price_data["ubicacion_analisis"].fillna("").astype(str).str.strip().ne("")]
    muni = muni.groupby(["fuente", "moneda_analisis", "ubicacion_analisis"]).agg(anuncios=("precio_analisis", "count"), mediana=("precio_analisis", "median")).reset_index()
    muni = muni[muni["anuncios"] >= 5]
    muni = muni.sort_values(["moneda_analisis", "mediana"], ascending=[True, False]).groupby("moneda_analisis", group_keys=False).head(10)
    lines.append(muni.to_markdown(index=False) if not muni.empty else "Sin suficentes datos.")
    lines.append("")

    if "fecha_reextraida" in master.columns:
        lines.append("### 2b. Frescura de los anuncios de Revolico")
        fechas = master[
            master["fuente"].eq("Revolico")
            & master["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
        ].copy()
        if not fechas.empty:
            fechas["mes_actualizacion"] = (
                fechas["fecha_reextraida"].astype(str).str.slice(0, 7)
            )
            frescura = fechas.groupby("mes_actualizacion").agg(anuncios=("id_maestro", "count")).reset_index()
            lines.append(
                f"Los {len(fechas)} anuncios de Revolico con fecha de pagina (`updatedOnByUser`) van del "
                f"{fechas['mes_actualizacion'].min()} al {fechas['mes_actualizacion'].max()}. "
                "Es la fecha de la ultima actualizacion del anuncio, no la de creacion ni la de venta; "
                "por tanto mide cuan frescos estan los anuncios, no cuando se cerraron operaciones."
            )
            lines.append("")
            lines.append(frescura.tail(12).to_markdown(index=False))
        else:
            lines.append("Sin fechas de pagina de anuncio aplicadas al maestro actual.")
        lines.append("")

    lines.append("## 3. Asociacion entre precio y caracteristicas")
    associations = rank_associations(price_data)
    if not associations.empty:
        lines.append("Correlacion de Spearman descriptiva, separada por fuente y moneda (n minimo 5):")
        lines.append(associations.to_markdown(index=False))
    else:
        lines.append("No hay pares completos suficientes para estimar asociaciones.")
    lines.append("")
    hab = price_data[price_data["habitaciones_analisis"].notna()].groupby(["fuente", "moneda_analisis", "habitaciones_analisis"])["precio_analisis"].agg(["count", "median"]).reset_index()
    lines.append("Medianas observadas por cantidad de habitaciones (mejor dato disponible: texto del anuncio, campo publicado o enlace):")
    lines.append(hab.to_markdown(index=False) if not hab.empty else "Sin pares completos.")
    lines.append("")
    baths = price_data[price_data["banos_analisis"].notna()].groupby(["fuente", "moneda_analisis", "banos_analisis"])["precio_analisis"].agg(["count", "median"]).reset_index()
    lines.append("Medianas observadas por cantidad de banos (mejor dato disponible: texto del anuncio, campo publicado o enlace):")
    lines.append(baths.to_markdown(index=False) if not baths.empty else "Sin pares completos.")
    lines.append("")

    lines.append("## 4. Características más frecuentes en viviendas caras")
    cub = price_data[price_data["fuente"] == "Cubisima"]
    for currency, currency_rows in cub.groupby("moneda_analisis"):
        high = currency_rows[currency_rows["precio_analisis"] >= currency_rows["precio_analisis"].median()]
        lines.append(f"Moneda **{currency}**: {len(high)} anuncios en o sobre la mediana de esa moneda.")
        for feature in ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]:
            if feature in high.columns:
                present = high[feature].astype(str).str.strip().str.lower().isin(["1", "true", "si", "sí", "yes"])
                lines.append(f"- **{feature}**: {int(present.sum())} de {len(high)} anuncios")
    if cub.empty:
        lines.append("Sin precios Cubisima utilizables con moneda identificada.")
    lines.append("")

    lines.append("## 5. Comparacion entre canales (informal vs estructurado)")
    def canal(row):
        if row["fuente"] == "Revolico":
            return "Informal - Revolico"
        if row["fuente"] == "Cubisima":
            return "Estructurado - Cubisima"
        return "Estructurado - HogarEnCuba"
    master["canal"] = master.apply(canal, axis=1)
    by_channel = price_data.groupby(["canal", "moneda_analisis"]).agg(
        anuncios=("precio_analisis", "count"),
        mediana_precio=("precio_analisis", "median"),
        con_habitaciones=("habitaciones_analisis", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        con_banos=("banos_analisis", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        fecha_pct=("fecha_publicacion", lambda s: round(100 * pd.notna(s).mean(), 1)),
    ).reset_index()
    lines.append(by_channel.to_markdown(index=False))
    lines.append("")
    common_currency = (
        price_data.groupby("moneda_analisis")["fuente"].nunique().loc[lambda values: values > 1].index.tolist()
    )
    lines.append(
        "Monedas observadas en mas de una fuente: "
        + (", ".join(common_currency) if common_currency else "ninguna")
        + ". Las diferencias entre fuentes solo son comparables dentro de la misma moneda; "
        "tambien pueden reflejar composicion y seleccion distintas de anuncios."
    )
    lines.append("")

    lines.append("## 6. Efecto de tasas sobre el precio equivalente")
    conversion_matches_master = (
        "dataset_maestro_origen" in conversion
        and conversion["dataset_maestro_origen"].nunique() == 1
        and conversion["dataset_maestro_origen"].iloc[0] == master_path.name
    )
    if conversion_matches_master:
        conv_stats = conversion.groupby(["fuente", "moneda_analisis"]).agg(
            anuncios=("precio_analisis", "count"),
            convertidos=("precio_usd_informal", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
            mediana_usd_informal=("precio_usd_informal", "median"),
            mediana_usd_formal=("precio_usd_formal", "median"),
            cuc_sin_tasa=("conversion_estado_informal", lambda s: int(s.eq("tasa_cuc_no_disponible").sum())),
        ).reset_index()
        lines.append(conv_stats.to_markdown(index=False))
        lines.append(f"\nDataset maestro usado para conversion: `{master_path.name}`")
        lines.append(
            "\nLa conversion CUC/USD nominal se identifica en `metodo_conversion_cuc` y no equivale a una tasa de mercado. "
            "Los importes originales y las tasas registradas se conservan por separado."
        )
    else:
        lines.append(
            "Se omiten estas conversiones: el archivo no acredita que use el dataset maestro actual. "
            "Vuelve a ejecutar convertir_precios_tasas.py después de reconstruir el maestro."
        )
    lines.append("")

    lines.append("## 7. Agrupaciones de viviendas")
    cluster_files = sorted((ROOT / "outputs" / "clustering").glob("clusters_*.csv"))
    if cluster_files:
        latest_cluster = cluster_files[-1]
        clusters = pd.read_csv(latest_cluster)
        grupos = clusters["cluster"].nunique()
        moneda_col = "moneda_analisis" if "moneda_analisis" in clusters else "moneda"
        detalle = "; ".join(
            f"{moneda}: {len(rows)} anuncios de {', '.join(sorted(rows['fuente'].unique()))}"
            for moneda, rows in clusters.groupby(moneda_col)
        )
        lines.append(
            "El script `clustering_viviendas.py` aplica k-means (k=3) por separado a cada moneda "
            "con al menos 30 observaciones, sobre el precio de analisis (que prefiere la reextraccion "
            "manual y excluye precios sospechosos), habitaciones y banos (mejor dato disponible: "
            "texto del anuncio, campo publicado o enlace). "
            f"Resultado vigente: `{latest_cluster.name}` con {grupos} grupos por moneda ({detalle}). "
            "Los centros estan en `centroides_clusters_*.csv`. "
            "Solo entran las monedas con 30 o mas observaciones completas; el resto se excluye y se anota."
        )
    else:
        lines.append(
            "El script `clustering_viviendas.py` aplica k-means por separado a cada moneda; "
            "aun no hay resultados guardados en `outputs/clustering/`."
        )
    lines.append("")

    lines.append("## 8. Migracion y mercado (tratamiento recomendado)")
    lines.append("Los anuncios transversales no permiten atribuir cambios de precio a la migracion ni estimar su efecto porcentual. "
                 "Este eje se triangula con entrevistas anonimas y fuentes historicas/contextuales, presentando las percepciones "
                 "como evidencia cualitativa, no como causalidad.")
    lines.append("")
    lines.extend(seccion_entrevistas())
    lines.append("")

    lines.append("## 9. Limites del proyecto")
    revolico = master[master["fuente"].eq("Revolico")]
    if not revolico.empty:
        total_revolico = len(revolico)
        municipio_campo = int(revolico["ubicacion_raw"].fillna("").astype(str).str.strip().ne("").sum())
        municipio_analisis = int(revolico["ubicacion_analisis"].fillna("").astype(str).str.strip().ne("").sum())
        fecha_reextraida = int(revolico["fecha_reextraida"].fillna("").astype(str).str.strip().ne("").sum())
        estado = revolico["estado_anuncio"].fillna("").astype(str).str.strip()
        borrados = int(estado.str.startswith("anuncio_inexistente").sum() + estado.eq("despublicado").sum())
        hab_analisis = int(pd.to_numeric(revolico.get("habitaciones_analisis"), errors="coerce").notna().sum())
        banos_analisis = int(pd.to_numeric(revolico.get("banos_analisis"), errors="coerce").notna().sum())
        publicados = int(estado.eq("publicado").sum())
        lines.append(
            f"- Municipio en Revolico: el campo publicado lo cubre {municipio_campo} de {total_revolico} "
            f"anuncios; la pagina del anuncio eleva la cobertura de analisis a {municipio_analisis}."
        )
        lines.append(
            f"- Fecha en Revolico: el campo publicado no la tiene; la pagina del anuncio aporta "
            f"`updatedOnByUser` en {fecha_reextraida} anuncios, que es fecha de actualizacion, no de creacion."
        )
        lines.append(
            f"- Habitaciones y banos en Revolico: se leen del texto del anuncio (descripcion, titulo y "
            f"enlace) ademas del campo publicado. El mejor dato disponible cubre {hab_analisis} de "
            f"{total_revolico} anuncios en habitaciones y {banos_analisis} en banos. El techo lo fija el "
            f"propio texto: {borrados} anuncios ya no estan accesibles y no tienen descripcion, y otros "
            f"anuncios publicados simplemente no mencionan la cantidad. No se imputa nada."
        )
        if borrados:
            lines.append(
                f"- Sesion de disponibilidad: {borrados} anuncios de Revolico ({publicados} siguen "
                "publicados) devolvieron un error de pagina al consultarlos el 2026-10-18; aun aparecian "
                "en el listado guardado del 2026-09-29, por lo que la desaparicion esta acotada a esa "
                "ventana. No se descartan: quedan marcados con su ventana y su justificacion."
            )
    lines.append(
        "- m2 excluido del analisis: ninguna fuente lo publica de forma sistemática (Revolico y Cubisima "
        "0%, HogarEnCuba ~5%); la columna se conserva en el maestro solo como traza de origen y su "
        "cobertura se reporta como hallazgo comparativo, no como variable explicativa."
    )
    lines.append("- El listado de Revolico esta bloqueado para scraping automatico; se usa HTML guardado.")
    lines.append("- Tasas online bloqueadas; se usa registro manual auditable.")
    lines.append("")
    lines.append("## 10. Linea narrativa de resultados (borrador, no informe final)")
    lines.append("")
    source_counts = master.groupby("fuente").size().to_dict()
    lines.append(
        f"La base integrada reune {len(master)} anuncios de tres canales: "
        + "; ".join(f"{source}: {count}" for source, count in source_counts.items())
        + ". La cobertura y la moneda difieren entre canales, por lo que el primer resultado defendible "
        "es describir cada fuente por separado y comparar precios solo dentro de monedas compartidas."
    )
    lines.append(
        "La asociacion entre caracteristicas y precio puede explorarse en los subconjuntos con observaciones completas; "
        "no describe causalidad y puede estar sesgada por la cobertura parcial de habitaciones y banos y por la ausencia "
        "de superficie utilizable."
    )
    lines.append(
        "La presion migratoria, los motivos de venta y la negociacion se abordan con las entrevistas anonimas "
        "disponibles como evidencia cualitativa (percepciones, no causalidad), contrastada con las medianas y "
        "agrupamientos anteriores. Este texto organiza resultados preliminares y no reemplaza el informe final."
    )
    lines.append("")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"preguntas_resueltas_{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Respuestas guardadas en: {path}")


if __name__ == "__main__":
    main()