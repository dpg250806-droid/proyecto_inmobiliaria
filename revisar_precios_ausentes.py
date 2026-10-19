#!/usr/bin/env python3
"""Busca precios ausentes en el texto de cada anuncio y aparta los intratables.

Para cada anuncio del maestro que no tiene precio de analisis:

1. Reunir el texto disponible: titulo y descripcion (Revolico usa el CSV local
   de detalle; Cubisima y las paginas publicadas de Revolico se consultan en
   la red porque su precio puede faltar en el listado pero aparecer en la
   pagina del anuncio, o al revés).
2. Extraer candidatos de precio con patrones conservadores: cantidad con
   moneda explicita (USD/CUC/EUR). Un importe solo con `$` no basta (puede ser
   USD o CUC), 7 o mas digitos sin separadores se trata como posible telefono,
   y si el texto trae mas de un importe distinto el anuncio no se resuelve
   solo.
3. Si hay un unico precio claro, distinto del campo publicado y en moneda con
   tasa documentada, se registra como recuperacion en
   `revision_manual/precios_ausentes.csv`; `integrar_fuentes.py` lo aplica como
   `precio_reextraido` con su evidencia (quien decide sigue siendo
   `precio_analisis`).
4. Todo lo demas (sin precio, ambiguo, moneda sin tasa, CUP por validar,
   pagina que no responde) queda en la lista pendiente
   `outputs/validacion/precios_pendientes_<fecha>.csv/.md` para revision
   manual. Tampoco se descarta ningun anuncio: la exclusion la hace
   `integrar_fuentes.py` por veredicto, no aqui.

No modifica ningun CSV original. Salidas fechadas en `outputs/validacion/`
mas `revision_manual/precios_ausentes.csv` (fijo, versionado).
"""
from __future__ import annotations

import argparse
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from precio_moneda import parsear_importe, precios_analisis
from revisar_descripciones_precios_bajos import obtener

ROOT = Path(__file__).resolve().parent
MAESTRO_DIR = ROOT / "outputs" / "integracion"
DETALLE_DIR = ROOT / "outputs" / "metadatos_revolico"
VALIDACION_DIR = ROOT / "outputs" / "validacion"
REVISION_SALIDA = ROOT / "revision_manual" / "precios_ausentes.csv"

ESPERA = 0.7

MONEDAS_POR_TEXTO = {
    "usd": "USD",
    "dolar": "USD",
    "dolares": "USD",
    "dólar": "USD",
    "dólares": "USD",
    "cuc": "CUC",
    "cup": "CUP",
    "mlc": "MLC",
    "euro": "EUR",
    "euros": "EUR",
    "\u20ac": "EUR",
}
# Monedas sin tasa documentada en el proyecto: no se recuperan solas.
MONEDAS_SIN_TASA = {"MLC"}

NUMERO = r"\d{1,3}(?:[.,\s\u00a0]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
# Cantidad con moneda detras, o moneda delante (incluido `$` ambiguo). La
# alternativa de `$` no se usa si tras la cantidad viene una moneda explicita:
# asi "Precio: $ 5000 USD" lo toma el patrón de "5000 USD" y no se pierde la
# moneda.
PATRON_CANDIDATO = re.compile(
    rf"(?P<n1>{NUMERO})\s*(?P<m1>usd|d[oó]lares?|cuc|cup|mlc|euros?|\u20ac)"
    rf"|(?P<m2>usd|d[oó]lares?|cuc|cup|mlc|euros?|\u20ac|\$)\s*"
    rf"(?P<n2>{NUMERO})\b(?!\s*(?:usd|d[oó]lares?|cuc|cup|mlc|euros?|\u20ac))",
    re.IGNORECASE,
)
# Precio embebido en la URL de Cubisima: "-25000-usd-" o "-10-cuc-".
PATRON_URL = re.compile(
    r"-(?P<n>(?:\d+-)*\d+)-(?P<m>usd|cuc|cup|eur)(?:-|[.!?]|$)", re.IGNORECASE
)
TELEFONO_DIGITOS = 7  # sin separadores: telefonos cubanos locales/ moviles


def cita_de(texto: str, inicio: int, fin: int, margen: int = 45) -> str:
    """Fragmento del texto alrededor de la coincidencia, para evidencia."""
    trozo = texto[max(0, inicio - margen) : min(len(texto), fin + margen)]
    return re.sub(r"\s+", " ", trozo).strip()


def candidatos_de_texto(texto: str, campo: str) -> tuple[list[dict], list[dict]]:
    """Extrae candidatos de precio de un texto; devuelve (candidatos, rechazados)."""
    candidatos: list[dict] = []
    rechazados: list[dict] = []
    if not texto:
        return candidatos, rechazados
    for coincidencia in PATRON_CANDIDATO.finditer(texto):
        crudo = coincidencia.group("n1") or coincidencia.group("n2") or ""
        moneda_texto = (coincidencia.group("m1") or coincidencia.group("m2") or "").lower()
        cita = cita_de(texto, coincidencia.start(), coincidencia.end())
        digitos = re.sub(r"\D", "", crudo)
        con_separador = ("." in crudo) or ("," in crudo)
        if len(digitos) >= TELEFONO_DIGITOS and not con_separador:
            rechazados.append(
                {"campo": campo, "crudo": crudo, "cita": cita,
                 "motivo": f"{len(digitos)} digitos sin separador: posible telefono"}
            )
            continue
        valor = parsear_importe(crudo)
        if valor is None:
            rechazados.append({"campo": campo, "crudo": crudo, "cita": cita,
                               "motivo": "cantidad ilegible"})
            continue
        candidatos.append(
            {
                "campo": campo,
                "valor": valor,
                "moneda": MONEDAS_POR_TEXTO.get(moneda_texto.rstrip("."), None),
                "moneda_texto": moneda_texto,
                "crudo": crudo,
                "cita": cita,
            }
        )
    return candidatos, rechazados


def candidatos_de_url(url: str) -> tuple[list[dict], list[dict]]:
    """Precios escritos en la propia URL (slugs de Cubisima)."""
    candidatos: list[dict] = []
    for coincidencia in PATRON_URL.finditer(url or ""):
        crudo = coincidencia.group("n").replace("-", "")
        valor = parsear_importe(crudo)
        if valor is None:
            continue
        moneda_texto = coincidencia.group("m").lower()
        candidatos.append(
            {
                "campo": "url",
                "valor": valor,
                "moneda": MONEDAS_POR_TEXTO.get(
                    "eur" if moneda_texto == "eur" else moneda_texto, None
                ),
                "moneda_texto": moneda_texto,
                "crudo": coincidencia.group(0),
                "cita": coincidencia.group(0),
            }
        )
    return candidatos, []


def resolver(
    candidatos: list[dict], rechazados: list[dict], publicado: float | None
) -> tuple[str, float | None, str, str]:
    """Decide el veredicto del anuncio a partir de sus candidatos.

    Devuelve `(veredicto, precio, moneda, detalle)`. Nunca elige entre
    importes distintos ni entre monedas ambiguas: eso queda para revision
    manual.
    """
    explicitos = [c for c in candidatos if c["moneda"]]
    if not explicitos:
        if any(c["moneda"] is None and c["moneda_texto"] == "$" for c in candidatos):
            return "moneda_ambigua", None, "", "$ sin moneda explicita: USD o CUC"
        if rechazados and not candidatos:
            motivos = "; ".join(sorted({r["motivo"] for r in rechazados}))
            return "solo_coincidencias_tipograficas", None, "", motivos
        return "sin_precio_en_texto", None, "", "ninguna cantidad con moneda en el texto"

    distintos = sorted({(c["valor"], c["moneda"]) for c in explicitos})
    if len(distintos) > 1:
        detalle = "; ".join(f"{v:g} {m}" for v, m in distintos)
        return "ambiguo", None, "", f"varios importes distintos: {detalle}"
    valor, moneda = distintos[0]
    if moneda in MONEDAS_SIN_TASA:
        return "moneda_sin_tasa", None, "", f"{valor:g} {moneda}: sin tasa documentada"
    if moneda == "CUP":
        return "cup_requiere_validacion", None, "", f"{valor:g} CUP: requiere validacion manual"
    if publicado is not None and valor == publicado:
        return (
            "solo_coincide_con_publicado",
            None,
            "",
            f"{valor:g} {moneda} igual al campo publicado ya marcado como sospechoso",
        )
    if valor < 100 or valor > 1_000_000:
        return "valor_improbable", None, "", f"{valor:g} {moneda}: fuera del rango verosimil"
    return "precio_recuperado", valor, moneda, f"unico importe explicito: {valor:g} {moneda}"


def aplicar_politica_consulta(
    veredicto: str,
    detalle: str,
    requiere_consulta: bool,
    estado_consulta: str,
    sin_descripcion_local: bool,
) -> tuple[str, str]:
    """Ajusta el veredicto segun que se pudo consultar; nunca adivina.

    Solo cambia el caso "no hay precio en el texto": si se pidio pagina y no
    se pudo ver, el veredicto pasa a consulta fallida; si la pagina se vio y
    esta viva (`publicado`/`published`), se afirma la ausencia con evidencia;
    si el anuncio ya no existe, se dice `anuncio_no_disponible`.
    """
    if veredicto != "sin_precio_en_texto":
        return veredicto, detalle
    if requiere_consulta:
        if estado_consulta == "no_consultado_sin_red":
            return "no_consultado_sin_red", "no se consulto la pagina (--sin-red)"
        if estado_consulta in ("publicado", "published"):
            # Pagina consultada y viva: efectivamente no cita precio.
            return veredicto, detalle
        if (
            estado_consulta == "despublicado"
            or estado_consulta.startswith("anuncio_inexistente")
            or estado_consulta == "sin_datos"
        ):
            return (
                "anuncio_no_disponible",
                "la pagina se consulto y el anuncio ya no esta disponible",
            )
        return "consulta_fallida", f"la pagina no se pudo consultar ({estado_consulta})"
    if sin_descripcion_local:
        return (
            "anuncio_no_disponible",
            "el anuncio ya no tiene descripcion accesible y el titulo no cita precio",
        )
    return veredicto, detalle


def ultimo(directorio: Path, patron: str) -> Path | None:
    candidatos = sorted(directorio.glob(patron))
    return candidatos[-1] if candidatos else None


def preparar_textos(
    fila,
    detalle_por_url: dict,
    sesion,
    sin_red: bool,
    espera: float,
) -> dict:
    """Devuelve textos, resultado de consulta y banderas de politica."""
    textos: dict[str, str] = {"titulo": str(fila.titulo or ""), "url": str(fila.url or "")}
    consulta = {"estado": "no_aplica", "precio_pagina": "", "descripcion_pagina": ""}
    requiere_consulta = False
    sin_descripcion_local = False

    if fila.fuente == "Revolico":
        local = detalle_por_url.get(fila.url)
        if local is not None and str(local.get("descripcion", "")).strip():
            textos["descripcion"] = str(local["descripcion"])
        else:
            sin_descripcion_local = True
        requiere_consulta = str(fila.estado_anuncio or "") == "publicado"
    elif fila.fuente == "Cubisima":
        # La pagina de Cubisima es la unica fuente de descripcion y de precio
        # cuando el listado no lo trae: siempre se consulta.
        requiere_consulta = True
    else:
        requiere_consulta = False

    if requiere_consulta:
        if sin_red:
            consulta["estado"] = "no_consultado_sin_red"
        else:
            resultado = obtener(str(fila.url), sesion)
            consulta["estado"] = str(resultado.get("estado", "sin_datos"))
            precio_pagina = str(resultado.get("precio_pagina", "") or "")
            if "None" in precio_pagina:
                precio_pagina = ""
            consulta["precio_pagina"] = precio_pagina
            consulta["descripcion_pagina"] = str(resultado.get("descripcion", "") or "")
            if espera:
                time.sleep(espera)

    # Descripcion a escanear: la local si existe; si no, la de la pagina.
    if "descripcion" not in textos and consulta["descripcion_pagina"]:
        textos["descripcion"] = consulta["descripcion_pagina"]
    if consulta["precio_pagina"]:
        textos["precio_pagina"] = consulta["precio_pagina"]
    textos["_requiere_consulta"] = requiere_consulta
    textos["_sin_descripcion_local"] = sin_descripcion_local
    textos["_estado_consulta"] = consulta["estado"]
    return textos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-red", action="store_true", help="No consulta paginas; deja 'no_consultado_sin_red'.")
    parser.add_argument("--espera", type=float, default=ESPERA, help="segundos entre peticiones")
    argumentos = parser.parse_args()

    ruta_maestro = ultimo(MAESTRO_DIR, "dataset_maestro_*.csv")
    if ruta_maestro is None:
        raise SystemExit(f"No hay maestro en {MAESTRO_DIR}: ejecuta integrar_fuentes.py")
    maestro = pd.read_csv(ruta_maestro, dtype=str).fillna("")
    precio, moneda = precios_analisis(maestro)
    buscar = maestro[precio.isna()].copy()
    print(f"Maestro: {ruta_maestro.name}")
    print(f"Anuncios sin precio de analisis: {len(buscar)}")

    ruta_detalle = ultimo(DETALLE_DIR, "detalle_anuncios_revolico_*.csv")
    detalle_por_url: dict[str, dict] = {}
    if ruta_detalle is not None:
        detalle = pd.read_csv(ruta_detalle, dtype=str).fillna("")
        detalle = detalle.drop_duplicates(subset=["url"], keep="last")
        detalle_por_url = {r.url: r._asdict() for r in detalle.itertuples(index=False)}
        print(f"Detalle local de Revolico: {ruta_detalle.name}")

    sesion = requests.Session()
    registros = []
    for numero, fila in enumerate(buscar.itertuples(index=False), start=1):
        textos = preparar_textos(fila, detalle_por_url, sesion, argumentos.sin_red, argumentos.espera)

        candidatos: list[dict] = []
        rechazados: list[dict] = []
        for campo in ("titulo", "descripcion", "precio_pagina"):
            nuevos, malos = candidatos_de_texto(textos.get(campo, ""), campo)
            candidatos += nuevos
            rechazados += malos
        nuevos_url, _ = candidatos_de_url(textos.get("url", ""))
        candidatos += nuevos_url

        # El campo publicado se interpreta con las mismas reglas que el texto.
        publicado = None
        if str(fila.precio_original or "").strip():
            publicado = parsear_importe(str(fila.precio_original))
            if publicado is None:
                try:
                    publicado = float(str(fila.precio_original))
                except ValueError:
                    publicado = None

        veredicto, valor_recuperado, moneda_recuperada, detalle_veredicto = resolver(
            candidatos, rechazados, publicado
        )

        # La politica de consulta separa "no tiene precio" de "no se pudo
        # consultar": lo primero solo se afirma con la pagina o el texto local
        # realmente consultados.
        veredicto, detalle_veredicto = aplicar_politica_consulta(
            veredicto,
            detalle_veredicto,
            bool(textos["_requiere_consulta"]),
            textos["_estado_consulta"],
            bool(textos["_sin_descripcion_local"]),
        )

        citas = " | ".join(dict.fromkeys(c["cita"] for c in candidatos))[:500]
        rechazos_txt = " | ".join(
            dict.fromkeys(f"{r['crudo']} ({r['motivo']})" for r in rechazados)
        )[:300]
        # Candidato que aporto el precio recuperado (para la evidencia).
        ganador = next(
            (
                c
                for c in candidatos
                if valor_recuperado is not None
                and c["valor"] == valor_recuperado
                and c["moneda"] == moneda_recuperada
            ),
            None,
        )
        if valor_recuperado is not None:
            observacion = (
                f"precio recuperado de {ganador['campo'] if ganador else 'texto'}: "
                f"{valor_recuperado:g} {moneda_recuperada} | "
                f"cita: {ganador['cita'] if ganador else citas} | "
                f"consulta: {textos['_estado_consulta']} | "
                f"metodo: revisar_precios_ausentes.py {datetime.now().strftime('%Y-%m-%d')}"
            )
        else:
            observacion = (
                f"{detalle_veredicto} | citas: {citas or 'ninguna'} | "
                f"rechazados: {rechazos_txt or 'ninguno'} | "
                f"consulta: {textos['_estado_consulta']} | "
                f"metodo: revisar_precios_ausentes.py {datetime.now().strftime('%Y-%m-%d')}"
            )
        registros.append(
            {
                "numero": numero,
                "fuente": fila.fuente,
                "id_local": fila.id_local,
                "url": fila.url,
                "veredicto": veredicto,
                "precio_titulo": fila.precio_original,
                "moneda_titulo": fila.moneda,
                "precio_pagina": textos.get("precio_pagina", ""),
                "precio_en_descripcion": "" if valor_recuperado is None else f"{valor_recuperado:g}",
                "moneda_en_descripcion": moneda_recuperada,
                "municipio": fila.municipio_reextraido,
                "estado": fila.estado_anuncio,
                "observacion": observacion,
                "fecha_revision": datetime.now().strftime("%Y-%m-%d"),
                # Columnas de evidencia para el informe de pendientes:
                "_titulo": fila.titulo,
                "_precio_publicado": fila.precio_original,
                "_moneda_publicada": fila.moneda,
                "_sospechoso": fila.precio_sospechoso,
                "_citas": citas,
                "_rechazados": rechazos_txt,
                "_consulta": textos["_estado_consulta"],
                "_descripcion": textos.get("descripcion", "")[:400],
            }
        )
        print(
            f"[{numero:03d}/{len(buscar)}] {veredicto:<32} "
            f"{('' if valor_recuperado is None else f'{valor_recuperado:g} {moneda_recuperada}'):<12} "
            f"{fila.fuente:<10} {fila.url[:55]}"
        )

    tabla = pd.DataFrame(registros)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    VALIDACION_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Lista de revision para integrar_fuentes.py (fija y versionada).
    columnas_revision = [
        "numero", "fuente", "id_local", "url", "veredicto", "precio_titulo",
        "moneda_titulo", "precio_pagina", "precio_en_descripcion",
        "moneda_en_descripcion", "municipio", "estado", "observacion",
        "fecha_revision",
    ]
    REVISION_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    # Reejecuciones: lo decidido en corridas anteriores (p. ej. los ya
    # recuperados, que al tener precio dejan de estar en la busqueda) se
    # conserva; esta corrida gana solo sobre los anuncios que volvio a evaluar.
    conservadas = pd.DataFrame(columns=columnas_revision)
    if REVISION_SALIDA.exists():
        previa = pd.read_csv(REVISION_SALIDA, dtype=str).fillna("")
        en_esta_corrida = set(tabla["url"])
        conservadas = previa[~previa["url"].isin(en_esta_corrida)].reindex(
            columns=columnas_revision
        ).fillna("")
        if not conservadas.empty:
            print(f"Decisiones conservadas de corridas anteriores: {len(conservadas)}")
    combinada = pd.concat([conservadas, tabla[columnas_revision]], ignore_index=True)
    combinada["numero"] = [str(i) for i in range(1, len(combinada) + 1)]
    combinada.to_csv(REVISION_SALIDA, index=False, encoding="utf-8-sig")

    # 2) Evidencia completa (candidatos, rechazos, consultas).
    salida_evidencia = VALIDACION_DIR / f"precios_ausentes_{marca}.csv"
    tabla.to_csv(salida_evidencia, index=False, encoding="utf-8-sig")

    # 3) Lista pendiente para revision manual de la persona investigadora.
    pendientes = tabla[tabla["veredicto"] != "precio_recuperado"].copy()
    salida_pendientes = VALIDACION_DIR / f"precios_pendientes_{marca}.csv"
    pendientes.to_csv(salida_pendientes, index=False, encoding="utf-8-sig")

    lineas = [
        "# Precios pendientes de revision manual",
        "",
        f"- Maestro consultado: `{ruta_maestro.name}`",
        f"- Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Sin precio de analisis: {len(tabla)} anuncios",
        f"- Recuperados automaticamente: {int((tabla['veredicto'] == 'precio_recuperado').sum())}",
        f"- Pendientes: {len(pendientes)}",
        "",
        "## Motivos de los pendientes",
        "",
    ]
    for motivo, cantidad in pendientes["veredicto"].value_counts().items():
        lineas.append(f"- `{motivo}`: {cantidad}")
    lineas.append("")
    for fila in pendientes.to_dict("records"):
        lineas.append(f"## [{fila['fuente']}] {fila['veredicto']}")
        lineas.append(f"- Titulo: {fila['_titulo']}")
        lineas.append(f"- URL: {fila['url']}")
        lineas.append(f"- Precio publicado: {fila['_precio_publicado'] or '(vacio)'} "
                      f"{fila['_moneda_publicada']} (sospechoso={fila['_sospechoso']})")
        lineas.append(f"- Candidatos descartados: {fila['_rechazados'] or 'ninguno'}")
        lineas.append(f"- Citas de precio en el texto: {fila['_citas'] or 'ninguna'}")
        lineas.append(f"- Consulta de pagina: {fila['_consulta']}")
        lineas.append(f"- Descripcion: {fila['_descripcion'] or '(sin descripcion)'}")
        lineas.append("")
    salida_md = VALIDACION_DIR / f"precios_pendientes_{marca}.md"
    salida_md.write_text("\n".join(lineas), encoding="utf-8")

    print()
    print("Veredictos:", dict(tabla["veredicto"].value_counts()))
    print(f"Revision (integracion): {REVISION_SALIDA}")
    print(f"Evidencia: {salida_evidencia}")
    print(f"Pendientes: {salida_pendientes}")
    print(f"Pendientes MD: {salida_md}")


if __name__ == "__main__":
    main()
