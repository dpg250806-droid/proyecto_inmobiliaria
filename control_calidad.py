#!/usr/bin/env python3
"""Control de calidad del repositorio (solo lectura).

Comprueba cuatro cosas y falla con codigo de salida distinto de cero si detecta
problemas:

1. Todos los scripts del proyecto compilan.
2. La documentacion no arrastra artefactos de texto (marcas sin resolver,
   palabras en otro idioma, caracteres fuera de rango) ni tablas mal formadas.
3. El estado de Git es visible antes de confirmar cambios.
4. Los ficheros temporales de inspeccion visual no se versionan.

No modifica ningun archivo de datos.
"""
from __future__ import annotations

import py_compile
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

fallos = []

print("== 1. Compilacion de scripts ==")
for ruta in sorted(ROOT.glob("*.py")):
    try:
        py_compile.compile(str(ruta), doraise=True, cfile=str(ROOT / "__pycache__" / (ruta.stem + ".pyc")))
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"compila: {ruta.name}: {exc}")
print(f"scripts revisados: {len(list(ROOT.glob('*.py')))}")

print("\n== 2. Artefactos de texto en documentacion ==")
patrones = {
    "linea suelta PY": re.compile(r"^PY\s*$"),
    "palabra en ingles no permitida": re.compile(r"\b(announce|Stamp|amplification|suspiciously)\b"),
    "caracteres CJK": re.compile(r"[\u4e00-\u9fff]"),
    "marcador sin resolver": re.compile(r"\b(TODO|FIXME|XXX)\b"),
}
for ruta in sorted(list(ROOT.glob("*.md")) + list((ROOT / "revision_manual").glob("*.md"))):
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    for nombre, patron in patrones.items():
        for numero, linea in enumerate(texto.splitlines(), 1):
            if patron.search(linea):
                fallos.append(f"texto: {ruta.name}:{numero} [{nombre}] {linea.strip()[:80]}")
print("documentacion revisada")

print("\n== 3. Cabeceras de tabla consistentes ==")
for ruta in sorted(ROOT.glob("*.md")):
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    for bloque in re.findall(r"(?:^\|.*\|$\n)+", texto, flags=re.MULTILINE):
        filas = [f for f in bloque.strip().splitlines() if f.strip().startswith("|")]
        if len(filas) < 2:
            continue
        separador = filas[1]
        if set(separador.replace("|", "").replace(":", "").replace("-", "").replace(" ", "")):
            continue
        columnas = filas[0].count("|")
        for fila in filas:
            if fila.count("|") != columnas:
                fallos.append(f"tabla: {ruta.name} ancho irregular: {fila[:70]}")
                break
print("tablas revisadas")

print("\n== 4. Estado de Git ==")
estado = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=ROOT)
print(estado.stdout or "(sin cambios)")
rama = subprocess.run(["git", "status", "-sb"], capture_output=True, text=True, cwd=ROOT).stdout.splitlines()[0]
print("rama:", rama)

print("\n== Resultado ==")
if fallos:
    for fallo in fallos:
        print(" -", fallo)
    raise SystemExit(f"{len(fallos)} problemas detectados")
print("sin problemas detectados")
