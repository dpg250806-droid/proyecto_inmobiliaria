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
    # La conversion con tasas y la nominal de CUC son archivos distintos: la
    # primera deja CUC sin tasa; la segunda anade la paridad nominal 1:1.
    conversion_path = latest(CONV_DIR, "dataset_maestro_conversion_2*.csv")
    nominal_files = sorted(CONV_DIR.glob("dataset_maestro_conversion_cuc_nominal_*.csv"))
    nominal_path = nominal_files[-1] if nominal_files else None
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
    if "municipio_homologado" not in master.columns:
        master["municipio_homologado"] = ""
    master["municipio_homologado"] = master["municipio_homologado"].fillna("").astype(str).str.strip()
    # Fecha de analisis: fecha publicada o, en Revolico, fecha recuperada de la pagina.
    master["fecha_analisis"] = (
        master["fecha_publicacion"].fillna("").astype(str).str.strip().ne("")
        | master["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
    )
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
    stats = (
        price_data.groupby(["fuente", "moneda_analisis"])["precio_analisis"]
        .agg(["count", "median", "mean", "min", "max"])
        .reset_index()
        .rename(
            columns={
                "count": "anuncios",
                "median": "mediana",
                "mean": "media",
                "min": "minimo",
                "max": "maximo",
            }
        )
    )
    for columna in ["mediana", "minimo", "maximo"]:
        stats[columna] = stats[columna].round(0).astype("Int64")
    stats["media"] = stats["media"].round(1)
    lines.append(stats.to_markdown(index=False))
    lines.append(
        "\nLa mediana es el centro robusto de cada grupo; la media se desplaza por valores extremos "
        "(por ejemplo, HogarEnCuba USD). No se comparan importes entre monedas. Las filas con n<10 "
        "(Cubisima USD n=8; EUR n=1 por fuente) se muestran para trazabilidad y no se interpretan."
    )
    lines.append("")

    lines.append("## 2. Precio por municipio homologado y por zona")
    municipios = price_data[price_data["municipio_homologado"].ne("")]
    if not municipios.empty:
        muni = municipios.groupby(["fuente", "moneda_analisis", "municipio_homologado"]).agg(
            anuncios=("precio_analisis", "count"),
            mediana=("precio_analisis", "median"),
        ).reset_index()
        muni = muni[muni["anuncios"] >= 5].sort_values(
            ["moneda_analisis", "fuente", "mediana"], ascending=[True, True, False]
        )
        lines.append(
            "Municipios de La Habana homologados (solo los 15 municipios; n>=5 por fuente y moneda). "
            "Las zonas o barrios que no son municipio quedan en la tabla siguiente y no se imputan. "
            "La tabla por fuente es la comparación válida; no se suma con la tabla de zonas:"
        )
        lines.append(muni.to_markdown(index=False) if not muni.empty else "Sin datos suficientes.")
        lines.append("")
        usd_muni = muni[muni["moneda_analisis"].eq("USD")]
        if {"Revolico", "HogarEnCuba"}.issubset(set(usd_muni["fuente"])):
            piv = usd_muni.pivot(index="municipio_homologado", columns="fuente", values="mediana")
            npiv = usd_muni.pivot(index="municipio_homologado", columns="fuente", values="anuncios")
            comunes = piv.dropna(subset=["Revolico", "HogarEnCuba"])
            if not comunes.empty:
                comparacion = pd.DataFrame(
                    {
                        "municipio": comunes.index,
                        "mediana_revolico": comunes["Revolico"].values,
                        "n_revolico": npiv.loc[comunes.index, "Revolico"].values,
                        "mediana_hogarencuba": comunes["HogarEnCuba"].values,
                        "n_hogarencuba": npiv.loc[comunes.index, "HogarEnCuba"].values,
                    }
                )
                comparacion["diferencia_pct"] = (
                    (comparacion["mediana_hogarencuba"] / comparacion["mediana_revolico"] - 1) * 100
                ).round(1)
                comparacion = comparacion.sort_values("mediana_revolico", ascending=False)
                lines.append(
                    "Comparación directa USD en municipios con n>=5 en ambas fuentes. La diferencia es "
                    "descriptiva, no causal: refleja composición y selección de anuncios, no un precio "
                    "único de mercado:"
                )
                lines.append(comparacion.to_markdown(index=False))
                lines.append("")
    else:
        lines.append("Sin municipios homologados en el maestro actual.")
    lines.append("")

    zonas = price_data[
        price_data["fuente"].eq("Cubisima")
        & price_data["ubicacion_analisis"].fillna("").astype(str).str.strip().ne("")
    ]
    if not zonas.empty:
        zona = zonas.groupby(["moneda_analisis", "ubicacion_analisis"]).agg(
            anuncios=("precio_analisis", "count"),
            mediana=("precio_analisis", "median"),
        ).reset_index()
        zona = zona[zona["anuncios"] >= 10]
        zona = zona.sort_values(["moneda_analisis", "mediana"], ascending=[True, False]).groupby(
            "moneda_analisis", group_keys=False
        ).head(10)
        lines.append(
            "Zonas o barrios de Cubisima (n>=10; se muestran las 10 medianas más altas por moneda). "
            "No son municipios: se muestran aparte para no mezclar niveles geográficos. Algunos "
            "nombres coinciden con municipios (Playa, Habana Vieja, Centro Habana), pero se conserva "
            "la etiqueta declarada por Cubisima."
        )
        lines.append(zona.to_markdown(index=False) if not zona.empty else "Sin datos suficientes.")
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
                f"Los {len(fechas)} anuncios de Revolico con fecha de página (`updatedOnByUser`) van del "
                f"{fechas['mes_actualizacion'].min()} al {fechas['mes_actualizacion'].max()}. "
                "Es la fecha de la última actualización del anuncio, no la de creación ni la de venta; "
                "por tanto mide cuán frescos están los anuncios, no cuándo se cerraron operaciones."
            )
            recientes = int(
                fechas["mes_actualizacion"].isin(["2026-08", "2026-09", "2026-10"]).sum()
            )
            lines.append(
                f"Del total, {recientes} de {len(fechas)} se actualizaron entre 2026-08 y 2026-10; "
                "la muestra temporal es casi toda de 2026, no un panel 2020-2026. No se usa para "
                "atribuir evolucion de precios."
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
        lines.append(
            "\nLas filas con 5 <= n < 10 son exploratorias y no se usan como evidencia en el informe; "
            "se conservan para trazabilidad. La correlacion no implica causalidad y puede estar "
            "afectada por la cobertura parcial de habitaciones y banos."
        )
    else:
        lines.append("No hay pares completos suficientes para estimar asociaciones.")
    lines.append("")
    hab = price_data[price_data["habitaciones_analisis"].notna()].groupby(["fuente", "moneda_analisis", "habitaciones_analisis"])["precio_analisis"].agg(["count", "median"]).reset_index()
    lines.append("Medianas observadas por cantidad de habitaciones (mejor dato disponible: texto del anuncio, campo publicado o enlace):")
    lines.append(hab.to_markdown(index=False) if not hab.empty else "Sin pares completos.")
    lines.append(
        "\nLas celdas con n<5 se muestran para trazabilidad, pero no se interpretan: una mediana con "
        "una o dos observaciones no es un patron."
    )
    lines.append("")
    baths = price_data[price_data["banos_analisis"].notna()].groupby(["fuente", "moneda_analisis", "banos_analisis"])["precio_analisis"].agg(["count", "median"]).reset_index()
    lines.append("Medianas observadas por cantidad de banos (mejor dato disponible: texto del anuncio, campo publicado o enlace):")
    lines.append(baths.to_markdown(index=False) if not baths.empty else "Sin pares completos.")
    lines.append(
        "\nLas celdas con n<5 se muestran para trazabilidad, pero no se interpretan. Los banos tienen "
        "menos cobertura que las habitaciones, sobre todo en Revolico."
    )
    lines.append("")

    lines.append("## 4. Características más frecuentes en viviendas caras")
    lines.append(
        "Solo Cubisima publica las características auxiliares (garaje, piscina, terraza, patio, "
        "balcón, jardín); Revolico y HogarEnCuba no las ofrecen de forma sistemática. Se compara "
        "el tercio superior de precio con el resto dentro de cada moneda. Es una asociación "
        "descriptiva, no causal. Un 0 significa que la característica no fue declarada en la ficha, "
        "no necesariamente que no exista."
    )
    cub = price_data[price_data["fuente"] == "Cubisima"]
    if cub.empty:
        lines.append("Sin precios Cubisima utilizables con moneda identificada.")
    else:
        def porcentaje_presente(series):
            return round(
                100
                * series.astype(str).str.strip().str.lower().isin(["1", "true", "si", "sí", "yes"]).mean(),
                1,
            )

        for currency, currency_rows in cub.groupby("moneda_analisis"):
            if len(currency_rows) < 10:
                lines.append(f"Moneda **{currency}**: n={len(currency_rows)}; no se calcula el tercio superior.")
                continue
            corte = currency_rows["precio_analisis"].quantile(0.66)
            alto = currency_rows[currency_rows["precio_analisis"] >= corte]
            resto = currency_rows[currency_rows["precio_analisis"] < corte]
            lines.append(
                f"Moneda **{currency}**: tercio superior n={len(alto)} (precio >= {corte:,.0f}); "
                f"resto n={len(resto)}."
            )
            filas = []
            etiquetas_caracteristicas = {
                "garaje": "Garaje",
                "piscina": "Piscina",
                "terraza": "Terraza",
                "patio": "Patio",
                "balcon": "Balcón",
                "jardin": "Jardín",
            }
            for feature in ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]:
                if feature not in currency_rows.columns:
                    continue
                pct_alto = porcentaje_presente(alto[feature])
                pct_resto = porcentaje_presente(resto[feature])
                filas.append(
                    {
                        "caracteristica": etiquetas_caracteristicas.get(feature, feature),
                        "pct_tercio_superior": pct_alto,
                        "pct_resto": pct_resto,
                        "diferencia_pp": round(pct_alto - pct_resto, 1),
                    }
                )
            if filas:
                lines.append(pd.DataFrame(filas).sort_values("diferencia_pp", ascending=False).to_markdown(index=False))
            lines.append("")
    lines.append("")

    lines.append("## 5. Comparación entre canales (informal vs estructurado)")
    def canal(row):
        if row["fuente"] == "Revolico":
            return "Informal - Revolico"
        if row["fuente"] == "Cubisima":
            return "Estructurado - Cubisima"
        return "Estructurado - HogarEnCuba"
    master["canal"] = master.apply(canal, axis=1)
    price_data["canal"] = price_data.apply(canal, axis=1)
    by_channel = price_data.groupby(["canal", "moneda_analisis"]).agg(
        anuncios=("precio_analisis", "count"),
        mediana_precio=("precio_analisis", "median"),
        con_habitaciones=("habitaciones_analisis", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        con_banos=("banos_analisis", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        fecha_publicada_pct=("fecha_publicacion", lambda s: round(100 * pd.notna(s).mean(), 1)),
        fecha_analisis_pct=("fecha_analisis", lambda s: round(100 * s.mean(), 1)),
    ).reset_index()
    lines.append(by_channel.to_markdown(index=False))
    lines.append(
        "\n`fecha_publicada_pct` mide el campo publicado; `fecha_analisis_pct` suma la fecha de "
        "actualización recuperada de la página individual en Revolico. No son equivalentes."
    )
    lines.append("")
    common_currency = (
        price_data.groupby("moneda_analisis")["fuente"].nunique().loc[lambda values: values > 1].index.tolist()
    )
    lines.append(
        "Monedas observadas en más de una fuente: "
        + (", ".join(common_currency) if common_currency else "ninguna")
        + ". Las diferencias entre fuentes solo son comparables dentro de la misma moneda; "
        "también pueden reflejar composición y selección distintas de anuncios."
    )
    eur = price_data[price_data["moneda_analisis"].eq("EUR")]
    if not eur.empty:
        lines.append(
            f"Atención: EUR suma n={len(eur)} en toda la muestra (2 fichas de HogarEnCuba y 1 de "
            "Cubisima). Se conserva por ser explícito en la descripción del vendedor, pero no se "
            "interpreta ni se usa para comparar canales."
        )
    lines.append(
        "La diferencia de medianas entre canales no controla por composición, zona, tamaño ni "
        "moneda del anuncio: describe lo que se publica en cada canal, no el efecto causal del canal."
    )
    lines.append("")

    lines.append("## 6. Efecto de tasas sobre el precio equivalente")
    conversion_matches_master = (
        "dataset_maestro_origen" in conversion
        and conversion["dataset_maestro_origen"].nunique() == 1
        and conversion["dataset_maestro_origen"].iloc[0] == master_path.name
    )
    nominal = None
    nominal_matches_master = False
    if nominal_path is not None:
        nominal = pd.read_csv(nominal_path, dtype=str)
        nominal_matches_master = (
            "dataset_maestro_origen" in nominal
            and nominal["dataset_maestro_origen"].nunique() == 1
            and nominal["dataset_maestro_origen"].iloc[0] == master_path.name
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
            f"Tasas registradas en `{conversion_path.name}`. USD y EUR se convierten con tasa informal "
            "y formal; CUC no tiene tasa de mercado registrada y queda sin convertir en ese archivo."
        )
        if nominal is not None and nominal_matches_master:
            nominal["precio_usd_informal"] = pd.to_numeric(nominal["precio_usd_informal"], errors="coerce")
            cuc = nominal[
                nominal["moneda_analisis"].eq("CUC")
                & nominal["conversion_estado_informal"].eq("convertido_nominal_1_CUC_1_USD")
            ]
            metodo = (
                str(cuc["metodo_conversion_cuc"].dropna().iloc[0])
                if cuc["metodo_conversion_cuc"].notna().any()
                else "paridad nominal 1 CUC = 1 USD"
            )
            mediana = cuc["precio_usd_informal"].median()
            lines.append(
                f"\nCUC: {len(cuc)} anuncios con precio de analisis se convierten a USD solo por "
                f"paridad nominal 1 CUC = 1 USD (`{metodo}`); mediana equivalente "
                f"{mediana:,.0f} USD. No es una tasa de mercado y no debe presentarse como "
                "conversion verificada."
            )
            lines.append(f"Archivo nominal usado: `{nominal_path.name}`")
        elif nominal_path is not None:
            lines.append(
                "\nLa conversion nominal de CUC no acredita el dataset maestro actual; no se cita."
            )
        else:
            lines.append("\nNo hay archivo de conversion nominal de CUC.")
        tasa_fecha = (
            str(conversion["fecha_tasa"].dropna().iloc[0])
            if "fecha_tasa" in conversion and conversion["fecha_tasa"].notna().any()
            else "fecha no registrada"
        )
        tasa_fuente = (
            str(conversion["fuente_tasa"].dropna().iloc[0])
            if "fuente_tasa" in conversion and conversion["fuente_tasa"].notna().any()
            else "fuente no registrada"
        )
        lines.append(
            f"\nTasas registradas: {tasa_fecha} ({tasa_fuente}). ElToque estaba bloqueado; se usan "
            "valores manuales auditables, no una tasa actualizada al corte. La conversion EUR de "
            "HogarEnCuba se apoya en n=2 y la de Cubisima en n=1: son ilustrativas, no estimaciones "
            "poblacionales."
        )
    else:
        lines.append(
            "Se omiten estas conversiones: el archivo no acredita que use el dataset maestro actual. "
            "Vuelve a ejecutar convertir_precios_tasas.py despues de reconstruir el maestro."
        )
    lines.append("")

    lines.append("## 7. Agrupaciones de viviendas")
    cluster_files = sorted((ROOT / "outputs" / "clustering").glob("clusters_*.csv"))
    if cluster_files:
        latest_cluster = cluster_files[-1]
        clusters = pd.read_csv(latest_cluster)
        moneda_col = "moneda_analisis" if "moneda_analisis" in clusters else "moneda"
        grupos = {
            str(moneda): int(rows["cluster"].nunique())
            for moneda, rows in clusters.groupby(moneda_col)
        }
        detalle = "; ".join(
            f"{moneda}: {len(rows)} anuncios de {', '.join(sorted(rows['fuente'].unique()))}"
            for moneda, rows in clusters.groupby(moneda_col)
        )
        completos = price_data.dropna(
            subset=["precio_analisis", "habitaciones_analisis", "banos_analisis"]
        )
        conteo = completos.groupby("moneda_analisis").size()
        incluidas = set(clusters[moneda_col].dropna().astype(str))
        excluidas = {
            str(moneda): int(cantidad)
            for moneda, cantidad in conteo.items()
            if str(moneda) not in incluidas and cantidad > 0
        }
        lines.append(
            "El script `clustering_viviendas.py` aplica k-means (k=3) por separado a cada moneda "
            "con al menos 30 observaciones completas, sobre el precio de analisis (que prefiere la "
            "reextraccion manual y excluye precios sospechosos), habitaciones y banos (mejor dato "
            "disponible: texto del anuncio, campo publicado o enlace). "
            f"Resultado vigente: `{latest_cluster.name}` con grupos por moneda {grupos} ({detalle}). "
            "Los grupos se renumeran por mediana de precio (0=económico, 1=medio, 2=alto) para que "
            "sean comparables entre monedas. Los centros estan en `centroides_clusters_*.csv`; "
            "`precio_medio` es el centroide (media devuelta a escala original), no la mediana del grupo."
        )
        centro_files = sorted((ROOT / "outputs" / "clustering").glob("centroides_clusters_*.csv"))
        if centro_files:
            centros = pd.read_csv(centro_files[-1])
            columnas = [
                columna
                for columna in [
                    "moneda",
                    "cluster",
                    "etiqueta",
                    "precio_medio",
                    "habitaciones_media",
                    "banos_media",
                ]
                if columna in centros.columns
            ]
            lines.append("")
            lines.append(f"Centroides vigentes (`{centro_files[-1].name}`):")
            lines.append(centros[columnas].to_markdown(index=False))
        if excluidas:
            lines.append(
                "\nMonedas con menos de 30 observaciones completas (no agrupadas): "
                + "; ".join(f"{moneda}: {cantidad}" for moneda, cantidad in excluidas.items())
                + "."
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
        "- Alcance: de las 1566 fichas iniciales se excluyeron 6 anuncios que no eran vivienda en "
        "venta (productos, permuta o local) y 28 fuera de alcance (13 en otras provincias y 15 que no "
        "son vivienda completa, incluidos cuartos sueltos). El maestro derivado queda en 1532. Las "
        "listas auditables estan en `revision_manual/exclusiones_alcance.csv` y en los CSV fechados "
        "`outputs/integracion/anuncios_no_residenciales_*.csv` y `anuncios_fuera_de_alcance_*.csv`."
    )
    lines.append(
        "- Alcance dudoso: 14 anuncios de uso mixto o dudoso (fincas, hostales, casas con restaurante "
        "o bar, almacenes y un local adaptado a vivienda) se conservan en el maestro porque la "
        "decision de excluirlos corresponde al usuario; quedan listados en "
        "`revision_manual/alcance_dudoso.csv` con motivo y evidencia."
    )
    lines.append(
        "- Precios pendientes: los anuncios sin precio de analisis se listan con su motivo y la accion "
        "sugerida en `outputs/validacion/precios_pendientes_actualizado_*.csv`; ningun valor se imputa."
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
        + ", despues de excluir 6 fichas que no eran vivienda en venta y 28 fuera de alcance "
        "(otras provincias o inmuebles no residenciales/cuartos). La cobertura y la moneda difieren "
        "entre canales, por lo que el primer resultado defendible es describir cada fuente por "
        "separado y comparar precios solo dentro de monedas compartidas."
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