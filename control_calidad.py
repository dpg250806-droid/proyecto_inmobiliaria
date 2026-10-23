#!/usr/bin/env python3
"""Control de calidad del repositorio (solo lectura).

Comprueba cuatro cosas y falla con codigo de salida distinto de cero si detecta
problemas:

1. Todos los scripts del proyecto compilan en memoria, sin crear bytecode.
2. La documentacion no arrastra artefactos de texto (marcas sin resolver,
   palabras en otro idioma, caracteres fuera de rango) ni tablas mal formadas.
3. El inventario de respaldos coincide con los archivos existentes.
4. El estado de Git es visible antes de confirmar cambios.

No modifica ningun archivo de datos.
"""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "data" / "raw" / "hash_inventario.csv"
RAW_DIR = INVENTORY.parent
FIXTURES_HISTORICOS_RETIRADOS = {"viviendas.csv", "viviendas_limpias.csv"}

fallos = []

print("== 1. Compilacion en memoria ==")
scripts = sorted(
    ruta
    for ruta in ROOT.rglob("*.py")
    if ".git" not in ruta.parts and "__pycache__" not in ruta.parts
)
for ruta in scripts:
    try:
        compile(ruta.read_bytes(), str(ruta), "exec")
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"compila: {ruta.name}: {exc}")
print(f"scripts revisados: {len(scripts)}")

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

print("\n== 4. Inventario de respaldos ==")
fixtures_ausentes = []
try:
    with INVENTORY.open("r", encoding="utf-8-sig", newline="") as archivo:
        inventario = csv.DictReader(archivo)
        for fila in inventario:
            nombre = fila["archivo"]
            ruta = RAW_DIR / nombre
            if not ruta.is_file():
                if nombre in FIXTURES_HISTORICOS_RETIRADOS:
                    fixtures_ausentes.append(nombre)
                else:
                    fallos.append(f"hash: archivo ausente: {nombre}")
                continue
            sha256 = hashlib.sha256(ruta.read_bytes()).hexdigest()
            if sha256.casefold() != fila["sha256"].strip().casefold():
                fallos.append(f"hash: no coincide: {nombre}")
            if ruta.stat().st_size != int(fila["bytes"]):
                fallos.append(f"hash: tamaño no coincide: {nombre}")
except (OSError, csv.Error, KeyError, ValueError) as exc:
    fallos.append(f"hash: no se pudo validar {INVENTORY.name}: {exc}")
print("hashes SHA-256 comparados sin distinguir mayusculas/minusculas")
if fixtures_ausentes:
    print(
        "fixtures historicos retirados, documentados y no tratados como error:",
        ", ".join(fixtures_ausentes),
    )

print("\n== 5. Estado de Git ==")
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
