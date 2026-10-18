"""Parseo conservador de importes y monedas publicados en anuncios."""

from __future__ import annotations

import re

import pandas as pd


_AMOUNT = r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_CURRENCY_PATTERNS = (
    ("CUC", re.compile(rf"\bCUC\s*({_AMOUNT})|({_AMOUNT})\s*CUC\b", re.IGNORECASE)),
    ("USD", re.compile(rf"(?:US\s*\$|\bUSD\s*\$?|\$)\s*({_AMOUNT})|({_AMOUNT})\s*(?:US\s*\$|\bUSD\b|\$)", re.IGNORECASE)),
    ("EUR", re.compile(rf"(?:€|\bEUR\b)\s*({_AMOUNT})|({_AMOUNT})\s*(?:€|\bEUR\b)", re.IGNORECASE)),
)
_CUC_URL = re.compile(r"-(\d+(?:[.,]\d+)?)-cuc(?:-|[.!?]|$)", re.IGNORECASE)


def normalizar_moneda(valor: str | None) -> str | None:
    """Normaliza códigos y representa las etiquetas de ausencia como desconocidas."""
    if valor is None:
        return None
    moneda = str(valor).strip().upper()
    return None if moneda in {"", "NAN", "NONE", "<NA>", "SIN_MONEDA"} else moneda


def parsear_importe(texto: str) -> float | None:
    """Interpreta separadores decimales y de miles habituales en anuncios."""
    valor = re.sub(r"[\s\u00a0]", "", texto)
    if not valor or not re.fullmatch(r"\d[\d.,]*", valor):
        return None

    ultima_coma = valor.rfind(",")
    ultimo_punto = valor.rfind(".")
    if ultima_coma >= 0 and ultimo_punto >= 0:
        decimal = max(ultima_coma, ultimo_punto)
        entero = re.sub(r"[.,]", "", valor[:decimal])
        fraccion = valor[decimal + 1 :]
        normalizado = f"{entero}.{fraccion}" if fraccion else entero
    elif ultima_coma >= 0 or ultimo_punto >= 0:
        separador = "," if ultima_coma >= 0 else "."
        posicion = valor.rfind(separador)
        digitos_finales = len(valor) - posicion - 1
        if digitos_finales in (1, 2):
            normalizado = valor[:posicion].replace(separador, "") + "." + valor[posicion + 1 :]
        else:
            normalizado = valor.replace(separador, "")
    else:
        normalizado = valor

    try:
        return float(normalizado)
    except ValueError:
        return None


def extraer_precio_moneda(texto: str, url: str | None = None) -> tuple[float | None, str | None]:
    """Devuelve importe y moneda solo cuando hay una señal monetaria explícita."""
    coincidencias: list[tuple[int, float, str]] = []
    for moneda, patron in _CURRENCY_PATTERNS:
        for encontrado in patron.finditer(texto or ""):
            crudo = encontrado.group(1) or encontrado.group(2)
            importe = parsear_importe(crudo)
            if importe is not None:
                coincidencias.append((encontrado.start(), importe, moneda))

    if not coincidencias:
        return None, None

    cuc_url = _CUC_URL.search(url or "")
    if cuc_url:
        importe_url = parsear_importe(cuc_url.group(1))
        for _, importe, _ in coincidencias:
            if importe == importe_url:
                return importe, "CUC"

    monedas = {moneda for _, _, moneda in coincidencias}
    if len(monedas) != 1:
        return None, None

    _, importe, moneda = min(coincidencias, key=lambda item: item[0])
    return importe, moneda


def precios_analisis(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Devuelve (precio, moneda) de analisis para cada fila del maestro.

    Reglas, en orden:
    1. Si existe una reextraccion manual (`precio_reextraido` con `moneda_reextraida`),
       se usa ese valor, que proviene de la descripcion o del titulo del anuncio.
    2. Si no, se usa el campo publicado (`precio_original`/`moneda`) salvo que este
       marcado como sospechoso.
    3. Un precio sospechoso sin reextraccion queda como NaN y sin moneda de analisis.

    Funciona tambien con maestros antiguos que no tienen las columnas de reextraccion.
    La cobertura de la fuente debe seguir midiendo `precio_original`; estas series
    miden el mejor precio disponible para analizar.
    """
    indice = frame.index
    reextraido = (
        pd.to_numeric(frame["precio_reextraido"], errors="coerce")
        if "precio_reextraido" in frame
        else pd.Series(float("nan"), index=indice)
    )
    moneda_reextraida = (
        frame["moneda_reextraida"].fillna("").astype(str).str.strip().str.upper()
        if "moneda_reextraida" in frame
        else pd.Series("", index=indice)
    )
    moneda_reextraida = moneda_reextraida.map(lambda valor: normalizar_moneda(valor) or "")
    campo = (
        pd.to_numeric(frame["precio_original"], errors="coerce")
        if "precio_original" in frame
        else pd.Series(float("nan"), index=indice)
    )
    moneda_campo = (
        frame["moneda"].fillna("").astype(str).map(lambda valor: normalizar_moneda(valor) or "")
        if "moneda" in frame
        else pd.Series("", index=indice)
    )
    sospechoso = (
        frame["precio_sospechoso"].fillna(False).astype(str).str.strip().str.lower().isin({"true", "1", "yes", "si", "sí"})
        if "precio_sospechoso" in frame
        else pd.Series(False, index=indice)
    )
    usable_campo = campo.notna() & moneda_campo.ne("") & ~sospechoso
    con_reextraccion = reextraido.notna() & moneda_reextraida.ne("")
    precio = reextraido.where(con_reextraccion, campo.where(usable_campo))
    moneda = moneda_reextraida.where(con_reextraccion, moneda_campo.where(usable_campo)).fillna("")
    return precio, moneda
