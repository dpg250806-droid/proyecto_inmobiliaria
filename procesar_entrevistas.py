#!/usr/bin/env python3
"""Procesa anonimamente entrevistas exportadas desde Google Forms (CSV o XLSX).

Reglas del proyecto:
- las respuestas se codifican como E01, E02, ... sin nombres ni correos;
- ninguna columna de metadatos personales se persiste (se descarta el correo si existiera);
- la salida es un CSV codificado mas un resumen MD fechados en `outputs/entrevistas/`.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from datetime import datetime
from pathlib import Path
import pandas as pd

QUESTIONS = {
    "Cuál es su relación con la vivienda?": "relacion",
    "En qué municipio se encuentra la vivienda con la que tiene mayor conocimiento?": "municipio",
    "En su opinión, ¿cómo han evolucionado los precios de las viviendas en Cuba desde 2020 hasta la actualidad? ¿A qué atribuye esos cambios?": "evolucion_precios",
    "¿Cuáles considera que son los principales factores que  determinan el precio de una vivienda en Cuba?": "factores_precio",
    "¿Qué influencia cree que tienen el USD, el EUR y las tasas de cambio oficiales e informales en la fijación de los precios de las viviendas?": "influencia_tasas",
    "¿Considera que los precios publicados en los anuncios inmobiliarios reflejan el valor real de las viviendas? ¿Por qué?": "refleja_precio",
    "¿Qué influencia considera que ha tenido la migración en la oferta, la demanda y los precios de las viviendas en Cuba durante el período del 2020 hasta el año actual?": "influencia_migracion",
    "Entre la crisis económica, las variaciones de las tasas de cambio y la migración, ¿cuál considera que ha influido más en el mercado inmobiliario cubano? ¿Por qué?": "factor_dominante",
    "¿Qué factores podrían llevar a una persona a reducir el precio solicitado por su vivienda o dificultar su venta?": "reduccion_precio",
    "¿Qué canales considera más efectivos para ofertar viviendas en Cuba y qué información debería incluir un anuncio para generar confianza?": "canales",
}

# Columnas de metadatos que jamas se persisten (privacidad).
PRIVACY_DROP = ("correo", "email", "nombre", "telefono", "whatsapp personal")

TIMESTAMP_COLS = ("marca temporal", "timestamp")


def normalize_key(text: str) -> str:
    """Clave comparable: NFKC, espacios colapsados, sin mayusculas sensibles."""
    text = unicodedata.normalize("NFKC", str(text))
    return re.sub(r"\s+", " ", text).strip()


def load_responses(path: Path) -> pd.DataFrame:
    """Lee el export del formulario (CSV o XLSX) como texto, sin tocar el original."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de entrevistas: {path}")
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        frame = pd.read_excel(path, dtype=str)
    elif suffix == ".csv":
        frame = pd.read_csv(path, dtype=str)
    else:
        raise ValueError(f"Formato no soportado para entrevistas: {suffix or '(sin extension)'}")
    return frame


def normalized_texts(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [normalize_key(c) for c in frame.columns]
    for col in frame.columns:
        frame[col] = frame[col].astype(str).str.replace("\n", " ").str.strip()
        frame[col] = frame[col].replace({"nan": "", "None": ""})
    return frame


def normalize_timestamp(value: str) -> str:
    """ISO legible cuando se puede parsear; si no, el texto original tal cual."""
    try:
        ts = pd.to_datetime(value, errors="coerce", format="mixed", dayfirst=True)
    except (ValueError, TypeError):
        ts = pd.NaT
    if pd.isna(ts):
        return str(value).strip()
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def prepare_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica privacidad, normaliza encabezados y renombra a las claves internas."""
    frame = normalized_texts(raw)

    # Privacidad: nunca se persisten metadatos personales.
    drop = [c for c in frame.columns if any(p in c.casefold() for p in PRIVACY_DROP)]
    if drop:
        frame = frame.drop(columns=drop)

    rename = {}
    for col in frame.columns:
        if normalize_key(col).casefold() in TIMESTAMP_COLS:
            rename[col] = "fecha_respuesta"
            continue
        target = QUESTIONS.get(col) or next(
            (v for k, v in QUESTIONS.items() if normalize_key(k) == col), None
        )
        if target:
            rename[col] = target
    frame = frame.rename(columns=rename)

    if "fecha_respuesta" in frame.columns:
        frame["fecha_respuesta"] = frame["fecha_respuesta"].map(normalize_timestamp)

    frame.insert(0, "entrevista_id", [f"E{i:02d}" for i in range(1, len(frame) + 1)])
    return frame


def plain_text(text: str) -> str:
    """Minusculas sin acentos ni enes, para que las palabras clave no dependan de tildes."""
    text = unicodedata.normalize("NFD", str(text).casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


# Municipios de La Habana (listado oficial) para C7; la busqueda es por palabras clave
# sobre el texto, no sobre la columna municipio, por lo que es una heuristica de frecuencia.
MUNICIPIOS_CLAVE = (
    "arroyo naranjo", "boyeros", "centro habana", "cerro", "diez de octubre", "10 de octubre",
    "guanabacoa", "habana del este", "habana vieja", "la lisa", "marianao", "playa", "plaza",
    "regla", "san miguel",
)


def code_row(row: pd.Series) -> dict:
    joined = " ".join(str(x) for x in row if isinstance(x, str))
    all_text = plain_text(joined)
    codes = {
        "C1_necesidad_economica": int(any(k in all_text for k in ("dinero", "necesidad", "urgencia", "misera"))),
        "C2_migracion": int(any(k in all_text for k in ("migra", "travesia", "nicaragua"))),
        "C3_moneda_tasa": int(any(k in all_text for k in ("usd", "cup", "tasas", "moneda"))),
        "C4_canal_venta": int(any(k in all_text for k in ("telegram", "whatsapp", "facebook", "grupo"))),
        "C5_precio_alto": int(any(k in all_text for k in ("caro", "carisimo", "regalo", "valor"))),
        "C6_caracteristicas": int(any(k in all_text for k in ("m2", "metro", "bano", "banos", "piscina"))),
        "C7_municipio": int(any(k in all_text for k in MUNICIPIOS_CLAVE)),
        "A1_cita": joined.lower()[:220],
    }
    return codes


def build_coded(frame: pd.DataFrame) -> pd.DataFrame:
    """Codifica las respuestas y anade los codigos C1..C7 + cita."""
    coded = frame.copy()
    code_frame = pd.DataFrame(list(coded.apply(code_row, axis=1)))
    return pd.concat([coded, code_frame], axis=1)


def build_summary(coded: pd.DataFrame) -> str:
    code_cols = [c for c in coded.columns if c.startswith("C") and c[1].isdigit()]
    lines = ["# Resumen de entrevistas", f"- Respuestas: {len(coded)}",
             f"- Columnas: {', '.join(coded.columns)}", "", "## Frecuencia de codigos"]
    for code in code_cols:
        lines.append(f"- {code}: {int(coded[code].sum())}")
    lines.append("")
    lines.append("## Relacion/municipio")
    if "relacion" in coded and "municipio" in coded:
        lines.append(coded.groupby(["relacion", "municipio"]).size().to_string())
    lines.append("")
    lines.append("## Factor dominante (respuesta literal)")
    if "factor_dominante" in coded:
        for _, row in coded.iterrows():
            lines.append(f"- **{row['entrevista_id']}**: {row['factor_dominante']}")
    lines.append("")
    lines.append("## Influencia de la migracion (respuesta literal)")
    if "influencia_migracion" in coded:
        for _, row in coded.iterrows():
            lines.append(f"- **{row['entrevista_id']}**: {row['influencia_migracion']}")
    lines.append("")
    lines.append("## Citas ilustrativas")
    for _, row in coded.iterrows():
        lines.append(f"- **{row['entrevista_id']}**: {row['A1_cita']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Procesa entrevistas anonimas de Google Forms (CSV o XLSX)")
    parser.add_argument("--csv", required=True, help="Ruta al export del formulario (.csv o .xlsx)")
    parser.add_argument("--outdir", default="outputs/entrevistas", help="Carpeta de salida")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    raw = load_responses(Path(args.csv))
    coded = build_coded(prepare_frame(raw))

    csv_path = outdir / f"entrevistas_codificadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    coded.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = build_summary(coded)
    summary_path = outdir / f"resumen_entrevistas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    summary_path.write_text(summary, encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"Resumen: {summary_path}")
    print("Criterios de codificacion:")
    code_cols = [c for c in coded.columns if c.startswith("C") and c[1].isdigit()]
    for code in code_cols:
        print(f"  {code}: {int(coded[code].sum())}")


if __name__ == "__main__":
    main()
