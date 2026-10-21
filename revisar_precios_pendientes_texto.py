"""Busca el precio real en el texto de los 134 anuncios pendientes de precio.

Para cada anuncio pendiente se recupera el texto ya descargado (descripcion de
la ficha de Cubisima cacheada y descripcion de la pagina de Revolico) y se
exponen los montos declarados, con un criterio mas laxo que el del script
original (que exigia moneda explicita). Sirve para decidir caso por caso.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "validacion"

# Montos con moneda explicita.
PATRONES = [
    re.compile(r"(\d[\d.,]*)\s*(?:usd|us\$|\$|dolares?|dólares?|eur|euros?|€|cuc|cup|mlc)\b", re.IGNORECASE),
    re.compile(r"\b(?:usd|us\$|\$|eur|euros?|€|cuc|cup|mlc)\s*(\d[\d.,]*)", re.IGNORECASE),
    re.compile(r"(\d[\d.,]*)\s*mil\b", re.IGNORECASE),
    re.compile(r"(\d[\d.,]*)\s*(?:de\s+)?(?:dolares|dolar|euros)\b", re.IGNORECASE),
]
CONTEXTO = re.compile(r"(precio|valor|vendo|vende|coste|cuesta|valoriza)[^.]{0,80}", re.IGNORECASE)


def montos(texto: str) -> str:
    if not isinstance(texto, str) or not texto.strip():
        return ""
    hallazgos = []
    for patron in PATRONES:
        for coincidencia in patron.finditer(texto):
            inicio = max(0, coincidencia.start() - 45)
            fin = min(len(texto), coincidencia.end() + 25)
            trozo = re.sub(r"\s+", " ", texto[inicio:fin]).strip()
            if trozo.lower() not in [h.lower() for h in hallazgos]:
                hallazgos.append(trozo)
    return " | ".join(hallazgos[:6])


def main() -> None:
    pendientes_path = sorted(OUT.glob("precios_pendientes_actualizado_*.csv"))[-1]
    pendientes = pd.read_csv(pendientes_path, dtype=str).fillna("")

    cache_cub = OUT / "alquileres_cubisima_cache.csv"
    textos_cub = {}
    if cache_cub.exists():
        cache = pd.read_csv(cache_cub, dtype=str).fillna("")
        textos_cub = cache.drop_duplicates("url").set_index("url")["descripcion"].to_dict()

    detalle = sorted((ROOT / "outputs" / "metadatos_revolico").glob("detalle_anuncios_revolico_*.csv"))[-1]
    rev = pd.read_csv(detalle, dtype=str).fillna("").drop_duplicates("url").set_index("url")
    textos_rev = rev["descripcion"].to_dict()

    filas = []
    for _, fila in pendientes.iterrows():
        url = fila["url"]
        if fila["fuente"] == "Cubisima":
            texto = textos_cub.get(url, "")
        else:
            texto = textos_rev.get(url, "")
            if not texto:
                texto = rev.loc[url, "titulo"] if url in rev.index else ""
        contexto = " | ".join(
            re.sub(r"\s+", " ", m).strip() for m in CONTEXTO.findall(texto or "")[:3]
        )
        filas.append(
            {
                "fuente": fila["fuente"],
                "id_local": fila["id_local"],
                "veredicto": fila["veredicto"],
                "precio_publicado": fila["precio_publicado"],
                "moneda_publicada": fila["moneda_publicada"],
                "titulo": fila["titulo"][:70],
                "tiene_texto": bool(texto),
                "montos": montos(texto),
                "contexto_precio": contexto,
                "url": url,
            }
        )

    salida = pd.DataFrame(filas)
    marca = "revision_precios_pendientes_texto"
    salida.to_csv(OUT / f"{marca}.csv", index=False, encoding="utf-8-sig")
    print(f"Escrito {OUT / (marca + '.csv')} con {len(salida)} filas")
    print("con texto local:", int(salida["tiene_texto"].sum()), "sin texto:", int((~salida["tiene_texto"]).sum()))
    print("con montos detectados:", int(salida["montos"].ne("").sum()))
    print()
    for fuente in ["Cubisima", "Revolico"]:
        print("=" * 110)
        for _, fila in salida[salida["fuente"].eq(fuente)].iterrows():
            print(
                f"[{fila['veredicto']:<26}] {fila['precio_publicado'] or '-':>8} {fila['moneda_publicada']:<4} | "
                f"{fila['titulo']}"
            )
            if fila["montos"]:
                print(f"      MONTOS: {fila['montos'][:400]}")
            if fila["contexto_precio"]:
                print(f"      CONTEXTO: {fila['contexto_precio'][:300]}")
            if not fila["tiene_texto"]:
                print("      (sin texto local)")


if __name__ == "__main__":
    main()
