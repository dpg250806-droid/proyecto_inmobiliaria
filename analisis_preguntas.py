#!/usr/bin/env python3
"""Genera respuestas tabuladas a las preguntas de investigacion."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
CONV_DIR = ROOT / "outputs" / "conversiones"
OUT = ROOT / "outputs" / "preguntas"


def latest(directory: Path, pattern: str) -> Path:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(directory / pattern)
    return files[-1]


def clean_boolean(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "si", "sí"])


def rank_associations(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (source, currency), group in frame.groupby(["fuente", "moneda"]):
        for field in ("habitaciones", "banos", "superficie_m2"):
            if field not in group:
                continue
            pair = group[["precio_original", field]].dropna()
            if len(pair) < 5 or pair[field].nunique() < 2 or pair["precio_original"].nunique() < 2:
                continue
            coefficient = pair["precio_original"].rank().corr(pair[field].rank())
            rows.append({
                "fuente": source,
                "moneda": currency,
                "variable": field,
                "n": len(pair),
                "spearman_rho": round(float(coefficient), 3),
            })
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master_path = latest(MASTER_DIR, "dataset_maestro_*.csv")
    conversion_path = latest(CONV_DIR, "dataset_maestro_conversion_*.csv")
    master = pd.read_csv(master_path, dtype=str)
    conversion = pd.read_csv(conversion_path, dtype=str)

    master["precio_original"] = pd.to_numeric(master["precio_original"], errors="coerce")
    master["habitaciones"] = pd.to_numeric(master["habitaciones"], errors="coerce")
    master["banos"] = pd.to_numeric(master["banos"], errors="coerce")
    master["superficie_m2"] = pd.to_numeric(master["superficie_m2"], errors="coerce")
    master["moneda"] = master["moneda"].fillna("").astype(str).str.strip().str.upper().replace("", "SIN_MONEDA")
    master["precio_sospechoso"] = clean_boolean(master["precio_sospechoso"])
    conversion["precio_usd_informal"] = pd.to_numeric(conversion["precio_usd_informal"], errors="coerce")
    conversion["precio_usd_formal"] = pd.to_numeric(conversion["precio_usd_formal"], errors="coerce")
    conversion["moneda"] = conversion["moneda"].fillna("").astype(str).str.strip().str.upper().replace("", "SIN_MONEDA")
    price_data = master[
        master["precio_original"].notna()
        & master["moneda"].ne("SIN_MONEDA")
        & ~master["precio_sospechoso"]
    ].copy()

    lines = []
    lines.append("# Analisis exploratorio y linea narrativa (no es el informe final)")
    lines.append("")
    lines.append(f"Dataset maestro: `{master_path.name}`")
    lines.append(f"Conversiones: `{conversion_path.name}`")
    lines.append(f"Filas en maestro: {len(master)}; precios utilizables (moneda conocida, no sospechosos): {len(price_data)}.")
    lines.append("")
    lines.append("## Evidencia y alcance de la muestra")
    lines.append("")
    coverage = master.groupby("fuente").agg(
        anuncios=("id_maestro", "count"),
        precio_disponible=("precio_original", "count"),
        ubicacion_disponible=("ubicacion_raw", "count"),
        habitaciones_disponibles=("habitaciones", "count"),
        banos_disponibles=("banos", "count"),
        superficie_disponible=("superficie_m2", "count"),
    ).reset_index()
    lines.append(coverage.to_markdown(index=False))
    lines.append("")
    lines.append("Distribucion de precios con moneda registrada:")
    lines.append("")
    currency_counts = master.groupby(["fuente", "moneda"], dropna=False).size().rename("anuncios").reset_index()
    lines.append(currency_counts.to_markdown(index=False))
    lines.append("")
    lines.append(
        "La unidad observada es un anuncio, no una transaccion cerrada. Los precios sospechosos, "
        "sin moneda o sin importe se excluyen de estadisticas de precios; no se imputan."
    )
    lines.append("")

    lines.append("## 1. Precio central por fuente y moneda")
    stats = price_data.groupby(["fuente", "moneda"])["precio_original"].agg(["count", "median", "mean", "min", "max"]).reset_index()
    lines.append(stats.to_markdown(index=False))
    lines.append("")

    lines.append("## 2. Precio por municipio/zona (top 10 por moneda, cobertura suficiente)")
    muni = price_data[price_data["ubicacion_raw"].notna()]
    muni = muni.groupby(["fuente", "moneda", "ubicacion_raw"]).agg(anuncios=("precio_original", "count"), mediana=("precio_original", "median")).reset_index()
    muni = muni[muni["anuncios"] >= 5]
    muni = muni.sort_values(["moneda", "mediana"], ascending=[True, False]).groupby("moneda", group_keys=False).head(10)
    lines.append(muni.to_markdown(index=False) if not muni.empty else "Sin suficentes datos.")
    lines.append("")

    lines.append("## 3. Asociacion entre precio y caracteristicas")
    associations = rank_associations(price_data)
    if not associations.empty:
        lines.append("Correlacion de Spearman descriptiva, separada por fuente y moneda (n minimo 5):")
        lines.append(associations.to_markdown(index=False))
    else:
        lines.append("No hay pares completos suficientes para estimar asociaciones.")
    lines.append("")
    hab = price_data[price_data["habitaciones"].notna()].groupby(["fuente", "moneda", "habitaciones"])["precio_original"].agg(["count", "median"]).reset_index()
    lines.append("Medianas observadas por cantidad de habitaciones:")
    lines.append(hab.to_markdown(index=False) if not hab.empty else "Sin pares completos.")
    lines.append("")
    baths = price_data[price_data["banos"].notna()].groupby(["fuente", "moneda", "banos"])["precio_original"].agg(["count", "median"]).reset_index()
    lines.append("Medianas observadas por cantidad de banos:")
    lines.append(baths.to_markdown(index=False) if not baths.empty else "Sin pares completos.")
    lines.append("")

    lines.append("## 4. CaracterÃ­sticas mÃ¡s frecuentes en viviendas caras")
    cub = price_data[price_data["fuente"] == "Cubisima"]
    for currency, currency_rows in cub.groupby("moneda"):
        high = currency_rows[currency_rows["precio_original"] >= currency_rows["precio_original"].median()]
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
    by_channel = price_data.groupby(["canal", "moneda"]).agg(
        anuncios=("precio_original", "count"),
        mediana_precio=("precio_original", "median"),
        metricas_m2=("superficie_m2", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        fecha_pct=("fecha_publicacion", lambda s: round(100 * pd.notna(s).mean(), 1)),
    ).reset_index()
    lines.append(by_channel.to_markdown(index=False))
    lines.append("")
    common_currency = (
        price_data.groupby("moneda")["fuente"].nunique().loc[lambda values: values > 1].index.tolist()
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
        conv_stats = conversion.groupby(["fuente", "moneda"]).agg(
            anuncios=("precio_original", "count"),
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
        detalle = "; ".join(
            f"{moneda}: {len(rows)} anuncios de {', '.join(sorted(rows['fuente'].unique()))}"
            for moneda, rows in clusters.groupby("moneda")
        )
        lines.append(
            "El script `clustering_viviendas.py` aplica k-means (k=3) por separado a cada moneda "
            "con al menos 30 observaciones, sobre precio, habitaciones y banos y sin precios sospechosos. "
            f"Resultado vigente: `{latest_cluster.name}` con {grupos} grupos por moneda ({detalle}). "
            "Los centros estan en `centroides_clusters_*.csv`. "
            "Revolico queda fuera por no tener banos y EUR por tener pocas observaciones."
        )
    else:
        lines.append(
            "El script `clustering_viviendas.py` aplica k-means por separado a cada moneda; "
            "aun no hay resultados guardados en `outputs/clustering/`."
        )
    lines.append("")

    lines.append("## 8. Migracion y mercado (tratamiento recomendado)")
    lines.append("Los anuncios transversales no permiten atribuir cambios de precio a la migracion ni estimar su efecto porcentual. "
                 "Este eje requiere triangular entrevistas anonimas con fuentes historicas/contextuales y presentar percepciones "
                 "como evidencia cualitativa, no como causalidad.")
    lines.append("")

    lines.append("## 9. Limites del proyecto")
    lines.append("- Municipio en Revolico: baja cobertura (37%).")
    lines.append("- m2 casi inexistente fuera de HogarEnCuba.")
    lines.append("- Fecha de publicacion inexistente en Revolico.")
    lines.append("- Revolico bloqueado para scraping automatico.")
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
        "no describe causalidad y puede estar sesgada por la falta de superficie y otras variables."
    )
    lines.append(
        "La interpretacion de la presion migratoria, motivos de venta y negociacion queda deliberadamente abierta "
        "hasta incorporar las entrevistas pendientes. Este texto organiza resultados preliminares y no reemplaza el informe final."
    )
    lines.append("")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"preguntas_resueltas_{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Respuestas guardadas en: {path}")


if __name__ == "__main__":
    main()