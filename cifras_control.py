#!/usr/bin/env python3
"""Cifras de control del maestro vigente (solo lectura).

Imprime los numeros que sostienen el informe: conteos por fuente, cobertura de
campos, precios por fuente y moneda, municipios, asociaciones, exclusiones de
alcance y pendientes de revision. No modifica ningun archivo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from precio_moneda import detalle_analisis, precios_analisis

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
REVISION_DIR = ROOT / "revision_manual"


def prepare_summary_groups(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply the documented minimum sample sizes to price summary tables."""
    currency_counts = frame.groupby("moneda_analisis").size()
    small_currencies = currency_counts[currency_counts < 5]
    frame = frame[frame["moneda_analisis"].isin(currency_counts[currency_counts >= 5].index)]
    pair_counts = frame.groupby(["fuente", "moneda_analisis"]).size()
    small_pairs = pair_counts[pair_counts < 10]
    eligible = pair_counts[pair_counts >= 10].index
    frame = frame[
        frame.set_index(["fuente", "moneda_analisis"]).index.isin(eligible)
    ].copy()
    excluded = {
        "monedas_n_menor_5": int(small_currencies.sum()),
        "pares_fuente_moneda_n_menor_10": int(small_pairs.sum()),
    }
    return frame, excluded


def newest(directory: Path, pattern: str) -> Path:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No hay archivos {pattern} en {directory}")
    return files[-1]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    master_path = newest(MASTER_DIR, "dataset_maestro_*.csv")
    master = pd.read_csv(master_path, dtype=str).fillna("")
    print("MAESTRO:", master_path.name, "| filas:", len(master))
    print("por fuente:", master["fuente"].value_counts().to_dict())
    print("ids duplicados:", int(master["id_maestro"].duplicated().sum()))
    print("urls duplicadas:", int(master["url"].duplicated().sum()))

    master["precio_original"] = pd.to_numeric(master["precio_original"], errors="coerce")
    master["precio_sospechoso"] = master["precio_sospechoso"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    master["precio_analisis"], master["moneda_analisis"] = precios_analisis(master)
    master["habitaciones_analisis"], master["banos_analisis"], _, _ = detalle_analisis(master)
    master["fecha_analisis"] = (
        master["fecha_publicacion"].fillna("").astype(str).str.strip().ne("")
        | master["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
    )
    master["ubicacion_analisis"] = master["ubicacion_analisis"].fillna("").astype(str).str.strip()
    master["municipio_homologado"] = master["municipio_homologado"].fillna("").astype(str).str.strip()

    print("\n== cobertura global ==")
    print("precio_analisis:", int(master["precio_analisis"].notna().sum()), "/", len(master))
    print("moneda_analisis:", master["moneda_analisis"].replace("", "SIN_MONEDA").value_counts().to_dict())
    print("moneda publicada:", master["moneda"].replace("", "SIN_MONEDA").value_counts().to_dict())
    print("origen_precio:", master["origen_precio"].value_counts().to_dict())
    print("precio_sospechoso:", int(master["precio_sospechoso"].sum()))
    sin_moneda_publicada = master["moneda"].fillna("").astype(str).str.strip().eq("")
    print(
        "sospechosos por motivo: sin moneda publicada",
        int((master["precio_sospechoso"] & sin_moneda_publicada).sum()),
        "| con problema de precio o moneda",
        int((master["precio_sospechoso"] & ~sin_moneda_publicada).sum()),
    )

    print("\n== por fuente (cobertura de analisis) ==")
    for fuente, grupo in master.groupby("fuente"):
        print(
            fuente,
            "n=",
            len(grupo),
            "| precio", int(grupo["precio_analisis"].notna().sum()),
            "| hab", int(pd.to_numeric(grupo["habitaciones_analisis"], errors="coerce").notna().sum()),
            "| banos", int(pd.to_numeric(grupo["banos_analisis"], errors="coerce").notna().sum()),
            "| ubicacion", int(grupo["ubicacion_analisis"].ne("").sum()),
            "| municipio_homologado", int(grupo["municipio_homologado"].ne("").sum()),
            "| fecha_publicada", int(grupo["fecha_publicacion"].astype(str).str.strip().ne("").sum()),
            "| fecha_analisis", int(grupo["fecha_analisis"].sum()),
        )

    print("\n== precios por fuente y moneda ==")
    usable = master[master["precio_analisis"].notna() & master["moneda_analisis"].ne("")]
    summary_prices, excluded_prices = prepare_summary_groups(usable)
    usable = summary_prices
    print(
        summary_prices.groupby(["fuente", "moneda_analisis"])["precio_analisis"]
        .agg(["count", "median", "mean", "min", "max"])
        .round(1)
        .to_string()
    )
    print("grupos omitidos por umbral:", excluded_prices)

    print("\n== asociacion de Spearman (habitaciones / banos vs precio) ==")
    filas = []
    for (fuente, moneda), grupo in usable.groupby(["fuente", "moneda_analisis"]):
        for campo in ["habitaciones_analisis", "banos_analisis"]:
            par = grupo[["precio_analisis", campo]].dropna()
            par[campo] = pd.to_numeric(par[campo], errors="coerce")
            par = par.dropna()
            if len(par) < 5 or par[campo].nunique() < 2:
                continue
            filas.append(
                {
                    "fuente": fuente,
                    "moneda": moneda,
                    "variable": campo,
                    "n": len(par),
                    "rho": round(par["precio_analisis"].rank().corr(par[campo].rank()), 3),
                }
            )
    asociaciones = pd.DataFrame(filas)
    print(
        asociaciones.sort_values(["variable", "fuente"]).to_string(index=False)
        if not asociaciones.empty
        else "Sin pares completos con tamaño suficiente."
    )

    print("\n== medianas por habitaciones (Revolico USD y Cubisima CUC) ==")
    for fuente, moneda in [("Revolico", "USD"), ("Cubisima", "CUC"), ("HogarEnCuba", "USD")]:
        sub = usable[
            usable["fuente"].eq(fuente)
            & usable["moneda_analisis"].eq(moneda)
            & pd.to_numeric(usable["habitaciones_analisis"], errors="coerce").notna()
        ]
        if sub.empty:
            continue
        tabla = (
            sub.assign(hab=lambda d: pd.to_numeric(d["habitaciones_analisis"], errors="coerce"))
            .groupby("hab")["precio_analisis"]
            .agg(["count", "median"])
            .round(0)
        )
        tabla = tabla[tabla["count"] >= 5]
        print(f"-- {fuente} {moneda}")
        print(tabla.to_string())

    print("\n== municipio homologado, USD, n>=5 por fuente ==")
    muni = usable[usable["moneda_analisis"].eq("USD") & usable["municipio_homologado"].ne("")]
    municipality_counts = muni.groupby(["municipio_homologado", "fuente"]).size()
    eligible_municipalities = municipality_counts[municipality_counts >= 5].index
    muni = muni[
        muni.set_index(["municipio_homologado", "fuente"]).index.isin(
            eligible_municipalities
        )
    ]
    tabla_muni = (
        muni.groupby(["municipio_homologado", "fuente"])["precio_analisis"]
        .agg(["count", "median"])
        .round(0)
    )
    tabla_muni = tabla_muni[tabla_muni["count"] >= 5]
    print(tabla_muni.to_string())

    print("\n== EUR (politica de conservacion) ==")
    print(
        master[master["moneda_analisis"].eq("EUR")][
            ["id_local", "titulo", "precio_original", "moneda", "precio_analisis", "origen_precio"]
        ].to_string(index=False)
    )

    print("\n== Revolico: estado y cobertura ==")
    rev = master[master["fuente"].eq("Revolico")]
    print("estado_anuncio:", rev["estado_anuncio"].replace("", "SIN_ESTADO").value_counts().to_dict())
    print("municipio campo publicado:", int(rev["ubicacion_raw"].astype(str).str.strip().ne("").sum()))
    print("municipio analisis:", int(rev["ubicacion_analisis"].ne("").sum()))
    print("fecha de pagina:", int(rev["fecha_reextraida"].astype(str).str.strip().ne("").sum()))
    print("origen precio:", rev["origen_precio"].value_counts().to_dict())
    fechas = rev[rev["fecha_reextraida"].astype(str).str.strip().ne("")].copy()
    if not fechas.empty:
        meses = fechas["fecha_reextraida"].astype(str).str.slice(0, 7)
        print("meses de actualizacion:", meses.value_counts().sort_index().to_dict())

    print("\n== Cubisima: fechas y monedas ==")
    cub = master[master["fuente"].eq("Cubisima")]
    print("moneda publicada:", cub["moneda"].replace("", "SIN_MONEDA").value_counts().to_dict())
    print("precio_analisis:", int(cub["precio_analisis"].notna().sum()), "de", len(cub))
    fechas_cub = pd.to_datetime(
        cub["fecha_publicacion"].replace("", pd.NA), format="%d/%m/%Y", errors="coerce"
    ).dropna()
    print("fecha Cubisima (dd/mm/yyyy) min/max:", fechas_cub.min().date(), fechas_cub.max().date())
    print("fechas Cubisima posteriores al corte (2026-10-19):", int((fechas_cub > pd.Timestamp("2026-10-19")).sum()))

    print("\n== HogarEnCuba: superficie y fechas ==")
    hec = master[master["fuente"].eq("HogarEnCuba")]
    print("m2 informado:", int(pd.to_numeric(hec["superficie_m2"], errors="coerce").notna().sum()), "de", len(hec))
    print("fecha relativa convertida:", int(hec["fecha_analisis"].sum()))

    print("\n== exclusiones de alcance ==")
    excl = pd.read_csv(newest(REVISION_DIR, "exclusiones_alcance.csv"), dtype=str).fillna("")
    urls = set(excl["url"].str.strip())
    print("filas de la auditoria:", len(excl))
    print("motivos:", excl["motivo"].value_counts().to_dict())
    print("URLs de exclusion presentes en el maestro (debe ser 0):", int(master["url"].isin(urls).sum()))

    print("\n== alcance dudoso conservado en el maestro ==")
    dudoso = pd.read_csv(newest(REVISION_DIR, "alcance_dudoso.csv"), dtype=str).fillna("")
    print("fichas:", len(dudoso))
    print("motivos:", dudoso["motivo"].value_counts().to_dict())
    print("presentes en el maestro:", int(dudoso["url"].isin(set(master["url"])).sum()))

    print("\n== pendientes de revision (veredictos del maestro) ==")
    print(master["veredicto_revision"].replace("", "(vacio)").value_counts().to_string())
    sin_precio = master[master["precio_analisis"].isna()]
    print("anuncios sin precio de analisis:", len(sin_precio))


if __name__ == "__main__":
    main()
