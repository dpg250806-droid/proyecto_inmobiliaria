#!/usr/bin/env python3
"""Normaliza precios a USD usando tasas informal y formal registradas."""
from __future__ import annotations

import math
from pathlib import Path
from datetime import datetime

import pandas as pd

ROOT = Path(__file__).resolve().parent
MASTER_DIR = ROOT / "outputs" / "integracion"
RATE_DIR = ROOT / "data" / "tasas"
OUT = ROOT / "outputs" / "conversiones"


def latest_file(directory: Path, pattern: str) -> Path:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No encontro {pattern} en {directory}")
    return files[-1]


def latest_rate_file(directory: Path, pattern: str) -> Path:
    """Snapshot de tasas mas reciente que contenga al menos una tasa USD.

    Un intento bloqueado de `tasas_cambio.py` guarda un registro de auditoria con
    las tasas vacias; ese archivo no debe reemplazar a un registro util.
    """
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No encontro {pattern} en {directory}")
    descartados = []
    for path in reversed(files):
        try:
            snapshot = pd.read_csv(path, dtype=str)
        except Exception:
            descartados.append(path.name)
            continue
        usd = snapshot.get("usd_informal_cup") if not snapshot.empty else None
        usable = usd is not None and pd.to_numeric(usd, errors="coerce").notna().any()
        if usable:
            if descartados:
                print("Snapshots de tasas descartados (sin tasa USD): " + ", ".join(descartados))
            return path
        descartados.append(path.name)
    raise ValueError(
        f"Ningun {pattern} en {directory} contiene una tasa USD registrada. "
        "Registra tasas manuales verificadas con tasas_cambio.py o carga el HTML local de ElToque."
    )


def to_float(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalizar_moneda(value):
    if pd.isna(value):
        return None
    currency = str(value).strip().upper()
    return None if currency in {"", "NAN", "NONE", "<NA>", "SIN_MONEDA"} else currency


# Anio de desmonetizacion del CUC: solo anuncios posteriores se valoran en USD.
CUC_DEMONETIZACION = pd.Timestamp("2021-01-01")
METODO_CUC_NOMINAL = (
    "nominal_1_CUC_igual_1_USD_anuncio_post_2021_confirmado_por_usuario_2026-10-18"
)


def parse_fecha_publicacion(value):
    """Fecha exacta de publicacion; None si no existe o es relativa."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return None
    if text.lower().startswith("actualizado"):
        return None  # fechas relativas de HogarEnCuba: no confirman el anio
    try:
        parsed = pd.to_datetime(text, format="%Y-%m-%d")
    except (ValueError, TypeError):
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    return None if pd.isna(parsed) else parsed


def convertir(
    frame: pd.DataFrame,
    rates: pd.DataFrame,
    master_filename: str | None = None,
    cuc_usd_nominal: bool = False,
) -> pd.DataFrame:
    if rates.empty:
        raise ValueError("El archivo de tasas no contiene registros.")
    r = rates.iloc[0]
    fx_usd_inf = to_float(r.get("usd_informal_cup"))
    fx_eur_inf = to_float(r.get("eur_informal_cup"))
    fx_cuc_inf = to_float(r.get("cuc_informal_cup"))
    fx_usd_for = to_float(r.get("usd_formal_cup"))
    fx_eur_for = to_float(r.get("eur_formal_cup"))
    fx_cuc_for = to_float(r.get("cuc_formal_cup"))
    fecha = str(r.get("fecha_utc", "sin_fecha"))

    def usd_price(row, fx_usd, fx_eur, fx_cuc):
        price = to_float(row.get("precio_original", None))
        moneda = normalizar_moneda(row.get("moneda", None))
        if price is None:
            return None, "precio_no_disponible"
        if bool(row.get("precio_sospechoso", False)):
            return None, "precio_sospechoso"
        if moneda == "USD":
            return price, "convertido"
        if moneda == "EUR":
            if fx_usd is None or fx_eur is None or fx_usd <= 0 or fx_eur <= 0:
                return None, "tasa_usd_eur_no_disponible"
            return price * fx_eur / fx_usd, "convertido"
        if moneda == "CUP":
            if fx_usd is None or fx_usd <= 0:
                return None, "tasa_usd_no_disponible"
            return price / fx_usd, "convertido"
        if moneda == "CUC":
            if cuc_usd_nominal:
                fecha_anuncio = parse_fecha_publicacion(row.get("fecha_publicacion", None))
                if fecha_anuncio is None:
                    return None, "sin_fecha_no_confirma_post_2021"
                if fecha_anuncio < CUC_DEMONETIZACION:
                    return None, "cuc_pre_2021_no_convertido"
                return price, "convertido_nominal_1_CUC_1_USD"
            if fx_cuc is None or fx_usd is None or fx_cuc <= 0 or fx_usd <= 0:
                return None, "tasa_cuc_no_disponible"
            return price * fx_cuc / fx_usd, "convertido"
        return None, "moneda_no_identificada" if not moneda else "moneda_no_soportada"

    frame = frame.copy()
    frame["precio_sospechoso"] = frame["precio_sospechoso"].astype(str).str.strip().str.lower().isin(["true", "1", "yes", "si", "sí"])
    informal = frame.apply(lambda row: usd_price(row, fx_usd_inf, fx_eur_inf, fx_cuc_inf), axis=1)
    formal = frame.apply(lambda row: usd_price(row, fx_usd_for, fx_eur_for, fx_cuc_for), axis=1)
    frame["precio_usd_informal"] = [result[0] for result in informal]
    frame["conversion_estado_informal"] = [result[1] for result in informal]
    frame["precio_usd_formal"] = [result[0] for result in formal]
    frame["conversion_estado_formal"] = [result[1] for result in formal]
    frame["fx_usd_informal_cup"] = fx_usd_inf
    frame["fx_eur_informal_cup"] = fx_eur_inf
    frame["fx_cuc_informal_cup"] = fx_cuc_inf
    frame["fx_usd_formal_cup"] = fx_usd_for
    frame["fx_eur_formal_cup"] = fx_eur_for
    frame["fx_cuc_formal_cup"] = fx_cuc_for
    frame["fecha_tasa"] = fecha
    frame["fuente_tasa"] = r.get("fuente")
    frame["fuente_cuc_tasa"] = r.get("fuente_cuc")
    if cuc_usd_nominal:
        cuc_rows = frame["moneda"].map(normalizar_moneda).eq("CUC")
        frame["metodo_conversion_cuc"] = None
        frame.loc[cuc_rows, "metodo_conversion_cuc"] = METODO_CUC_NOMINAL
        frame["fx_cuc_usd_nominal"] = None
        convertidos_cuc = frame["conversion_estado_informal"].eq(
            "convertido_nominal_1_CUC_1_USD"
        ) | frame["conversion_estado_formal"].eq("convertido_nominal_1_CUC_1_USD")
        frame.loc[convertidos_cuc, "fx_cuc_usd_nominal"] = 1.0
    if master_filename:
        frame["dataset_maestro_origen"] = master_filename
    frame["divergencia_informal_formal_usd_pct"] = 100 * (frame["precio_usd_informal"] / frame["precio_usd_formal"] - 1)
    return frame


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Normaliza precios a USD con tasas registradas.")
    parser.add_argument(
        "--cuc-usd-nominal",
        action="store_true",
        help=(
            "Convierte CUC a USD (1:1, no es una tasa de mercado) solo en anuncios "
            "con fecha de publicacion posterior a 2021."
        ),
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    master_path = latest_file(MASTER_DIR, "dataset_maestro_*.csv")
    rate_path = latest_rate_file(RATE_DIR, "tasas_cambio_*.csv")
    frame = pd.read_csv(master_path, dtype=str)
    rates = pd.read_csv(rate_path, dtype=str)
    converted = convertir(frame, rates, master_path.name, cuc_usd_nominal=args.cuc_usd_nominal)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_cuc_nominal" if args.cuc_usd_nominal else ""
    output = OUT / f"dataset_maestro_conversion{suffix}_{stamp}.csv"
    with output.open("x", encoding="utf-8-sig", newline="") as handle:
        converted.to_csv(handle, index=False)

    stats = converted.groupby(["fuente", "moneda"]).agg(
        anuncios=("precio_original", "count"),
        convertidos_usd_informal=("precio_usd_informal", lambda s: pd.notna(s).sum()),
        mediana_usd_informal=("precio_usd_informal", "median"),
        mediana_usd_formal=("precio_usd_formal", "median"),
        cuc_sin_tasa=("conversion_estado_informal", lambda s: int(s.eq("tasa_cuc_no_disponible").sum())),
        cuc_no_post_2021=(
            "conversion_estado_informal",
            lambda s: int(s.isin(["cuc_pre_2021_no_convertido", "sin_fecha_no_confirma_post_2021"]).sum()),
        ),
    ).reset_index()
    stats_path = OUT / f"resumen_conversion{suffix}_{stamp}.csv"
    with stats_path.open("x", encoding="utf-8-sig", newline="") as handle:
        stats.to_csv(handle, index=False)

    print(f"Dataset con conversion: {output}")
    print(f"Mediana informal/formal guardada en: {stats_path}")
    print(stats.to_string(index=False))


if __name__ == "__main__":
    main()