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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(latest(MASTER_DIR, "dataset_maestro_*.csv"), dtype=str)
    conversion = pd.read_csv(latest(CONV_DIR, "dataset_maestro_conversion_*.csv"), dtype=str)

    master["precio_original"] = pd.to_numeric(master["precio_original"], errors="coerce")
    master["habitaciones"] = pd.to_numeric(master["habitaciones"], errors="coerce")
    master["banos"] = pd.to_numeric(master["banos"], errors="coerce")
    conversion["precio_usd_informal"] = pd.to_numeric(conversion["precio_usd_informal"], errors="coerce")
    conversion["precio_usd_formal"] = pd.to_numeric(conversion["precio_usd_formal"], errors="coerce")

    lines = []
    lines.append("# Respuestas tabuladas a las preguntas de investigacion")
    lines.append("")
    lines.append(f"Dataset maestro: `{latest(MASTER_DIR, 'dataset_maestro_*.csv').name}`")
    lines.append(f"Conversiones: `{latest(CONV_DIR, 'dataset_maestro_conversion_*.csv').name}`")
    lines.append("")

    lines.append("## 1. Precio central por fuente y moneda")
    stats = master.groupby(["fuente", "moneda"])["precio_original"].agg(["count", "median", "mean", "min", "max"]).reset_index()
    lines.append(stats.to_markdown(index=False))
    lines.append("")

    lines.append("## 2. Precio por municipio/zona (top 10 con cobertura suficiente)")
    muni = master[master["ubicacion_raw"].notna() & master["precio_original"].notna()]
    muni = muni.groupby(["fuente", "ubicacion_raw"]).agg(anuncios=("precio_original", "count"), mediana=("precio_original", "median")).reset_index()
    muni = muni[muni["anuncios"] >= 5].sort_values("mediana", ascending=False).head(10)
    lines.append(muni.to_markdown(index=False) if not muni.empty else "Sin suficentes datos.")
    lines.append("")

    lines.append("## 3. Habitaciones y baÃ±os vs precio")
    hab = master[master["habitaciones"].notna() & master["precio_original"].notna()].groupby("habitaciones")["precio_original"].agg(["count", "median"]).reset_index()
    lines.append("Habitaciones:")
    lines.append(hab.to_markdown(index=False))
    lines.append("")

    lines.append("## 4. CaracterÃ­sticas mÃ¡s frecuentes en viviendas caras")
    cub = master[(master["fuente"] == "Cubisima")]
    if not cub.empty:
        med = cub["precio_original"].median()
        high = cub[cub["precio_original"] >= med]
        for feature in ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]:
            if feature in high.columns:
                lines.append(f"- **{feature}**: {int(pd.to_numeric(high[feature], errors='coerce').fillna(0).sum())} anuncios de {len(high)}")
    lines.append("")

    lines.append("## 5. ComparaciÃ³n entre canales (informal vs estructurado)")
    def canal(row):
        if row["fuente"] == "Revolico":
            return "Informal - Revolico"
        if row["fuente"] == "Cubisima":
            return "Estructurado - Cubisima"
        return "Formal/estructurado - HogarEnCuba"
    master["canal"] = master.apply(canal, axis=1)
    by_channel = master.groupby("canal").agg(
        anuncios=("precio_original", "count"),
        mediana_precio=("precio_original", "median"),
        metricas_m2=("superficie_m2", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        fecha_pct=("fecha_publicacion", lambda s: round(100 * pd.notna(s).mean(), 1)),
    ).reset_index()
    lines.append(by_channel.to_markdown())
    lines.append("")

    lines.append("## 6. Efecto de tasas sobre el precio equivalente")
    conv_stats = conversion.groupby(["fuente", "moneda"]).agg(
        anuncios=("precio_original", "count"),
        convertidos=("precio_usd_informal", lambda s: pd.to_numeric(s, errors="coerce").notna().sum()),
        mediana_usd_informal=("precio_usd_informal", "median"),
        mediana_usd_formal=("precio_usd_formal", "median"),
    ).reset_index()
    lines.append(conv_stats.to_markdown(index=False))
    lines.append(
        "\nLa divergencia entre tasas implica que el mismo precio publicado cambia de valor equivalente en USD, "
        "lo que afecta la interpretacion del mercado."
    )
    lines.append("")

    lines.append("## 7. Agrupaciones de viviendas")
    lines.append("No se ejecuto un clustering en esta etapa. Se necesitan variables completas y una estrategia de imputacion documentada para habitaciones/banos/superficie.")
    lines.append("")

    lines.append("## 8. Migracion y mercado (tratamiento recomendado)")
    lines.append("No se puede atribuir porcentualmente a la migraciÃ³n con anuncios transversales. Se recomienda analisis contextual + entrevistas + series oficiales.")
    lines.append("")

    lines.append("## 9. Limites del proyecto")
    lines.append("- Municipio en Revolico: baja cobertura (37%).")
    lines.append("- m2 casi inexistente fuera de HogarEnCuba.")
    lines.append("- Fecha de publicacion inexistente en Revolico.")
    lines.append("- Revolico bloqueado para scraping automatico.")
    lines.append("- Tasas online bloqueadas; se usa registro manual auditable.")
    lines.append("")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"preguntas_resueltas_{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Respuestas guardadas en: {path}")


if __name__ == "__main__":
    main()