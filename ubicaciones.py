#!/usr/bin/env python3
"""Homologacion de municipios de La Habana.

Revolico, Cubisima y HogarEnCuba nombran los municipios con variantes
("Plaza", "Plaza de la Revolución", "Plaza De La Revolucion"). Para comparar
entre fuentes se necesita una sola etiqueta canonica. Las zonas o barrios que
no son municipios (Vedado, Miramar, Santa Clara, ...) devuelven cadena vacia:
no se imputa un municipio que la fuente no declara.
"""
from __future__ import annotations

import re
import unicodedata

MUNICIPIOS_HABANA = (
    "Arroyo Naranjo",
    "Boyeros",
    "Centro Habana",
    "Cerro",
    "Cotorro",
    "Diez de Octubre",
    "Guanabacoa",
    "Habana del Este",
    "Habana Vieja",
    "La Lisa",
    "Marianao",
    "Playa",
    "Plaza de la Revolución",
    "Regla",
    "San Miguel del Padrón",
)


def _clave(valor: str | None) -> str:
    """Minusculas, sin acentos ni puntuacion, para comparar variantes."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = texto.lower().replace("ñ", "n")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


_ALIASES = {
    # Plaza de la Revolucion: Revolico usa "Plaza"; HogarEnCuba la forma larga.
    "plaza": "Plaza de la Revolución",
    "plaza de la revolucion": "Plaza de la Revolución",
    "plaza revolucion": "Plaza de la Revolución",
    # Habana Vieja y Habana del Este aparecen con y sin articulo.
    "habana vieja": "Habana Vieja",
    "la habana vieja": "Habana Vieja",
    "habana del este": "Habana del Este",
    "la habana del este": "Habana del Este",
    # Diez de Octubre aparece como "10 de Octubre" en algunas zonas.
    "diez de octubre": "Diez de Octubre",
    "10 de octubre": "Diez de Octubre",
    # San Miguel del Padron se publica con y sin tilde.
    "san miguel del padron": "San Miguel del Padrón",
    # Formas ya canonicas que solo requieren normalizar.
    "arroyo naranjo": "Arroyo Naranjo",
    "boyeros": "Boyeros",
    "centro habana": "Centro Habana",
    "cerro": "Cerro",
    "cotorro": "Cotorro",
    "guanabacoa": "Guanabacoa",
    "la lisa": "La Lisa",
    "marianao": "Marianao",
    "playa": "Playa",
    "regla": "Regla",
}


def homologar_municipio(valor: str | None) -> str:
    """Devuelve el municipio canonico de La Habana o '' si no es municipio."""
    return _ALIASES.get(_clave(valor), "")


def es_municipio_habana(valor: str | None) -> bool:
    """True si el valor corresponde a uno de los 15 municipios de La Habana."""
    return homologar_municipio(valor) != ""
