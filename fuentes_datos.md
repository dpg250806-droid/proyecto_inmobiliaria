# Fuentes cubanas de viviendas: estado de verificación

**Actualizado:** 20/10/2026 · **Corte de datos:** 19/10/2026.

Resumen de la decisión de fuentes: **Revolico** aporta volumen y es el clasificado informal; **Cubisima** aporta estructura y es la única fuente masiva en CUC; **HogarEnCuba** aporta fichas estructuradas de precio más alto. Las demás fuentes quedan como candidatas future y no entran en el análisis actual.

## 1. Revolico (fuente principal, informal)

- URL base usada: `https://www.revolico.com/search?category=inmobiliaria&subcategory=inmobiliaria-casas&province=la-habana`
- Estado online: **bloqueado por Cloudflare/anti-bot** para scraping automático (HTTP 403; Playwright y Selenium reciben la página "Un momento..."). Solución operativa: guardar las páginas HTML y procesarlas localmente.
- Datos actuales: 780 anuncios únicos extraídos de 8 páginas HTML locales; **755** entran al maestro vigente tras las exclusiones de alcance.
- La **página individual de cada anuncio sí responde**: de ahí se extraen municipio, fecha (`updatedOnByUser`) y descripción completa, y con el texto se reconstruyen habitaciones y baños.
- Fortaleza: gran volumen y precios en USD.
- Limitaciones: municipio ausente en el campo publicado (38,0 % de cobertura), habitaciones en 9,1 %, banos en 0 % y fecha en 0 %; superficie nunca. 153 de 755 anuncios ya no son accesibles (80 despublicados, 73 eliminados).

## 2. Cubisima (fuente estructurada complementaria)

- URL base usada: `https://www.cubisima.com/casas/anuncios/la-habana/`
- Estado online: **accesible** con `requests`.
- Snapshot en `outputs/cubisima/` y copia local `viviendas_cubisima.csv` con 625 filas; **594** entran al maestro vigente.
- Campos observados: tipo, zona, habitaciones, baños, precio, moneda, fecha y seis características auxiliares (garaje, piscina, terraza, patio, balcón, jardín).
- Fechas en `dd/mm/yyyy` entre 17/10/2023 y 12/10/2026; ninguna posterior al corte.
- Fortaleza: más variables estructuradas que Revolico y única fuente masiva en CUC.
- Limitaciones: la zona mezcla municipios y barrios (solo 100 fichas coinciden con un municipio de La Habana); no publica superficie; 51 fichas sin moneda publicada y 58 sin precio de análisis; no hay tasa CUC/CUP verificada, por lo que la conversión a USD usa una **paridad nominal declarada** (1 CUC = 1 USD), no una tasa de mercado, y solo sobre anuncios posteriores a 2021.

## 3. HogarEnCuba (fuente estructurada complementaria)

- URL observada: `https://hogarencuba.com/ventas/la-habana`
- Estado: página accesible; captura reproducible con `scraper_hogarencuba.py` (10/10 páginas, 0 fallidas) → **188 fichas** en el snapshot vigente; **183** entran al maestro.
- Fortaleza: cobertura estructurada del 100 % (precio, habitaciones, baños, ubicación) y es la **única fuente que publica superficie**, aunque solo en 9 de 183 fichas (4,9 %).
- Limitaciones: volumen menor, **fechas relativas** ("hace 2 años": 162 de 183 convertidas, no exactas) y 14 fichas con precio o moneda discordante entre JSON-LD y cuerpo del anuncio. Cuando el cuerpo declara "PRECIO EN EUR" (`HEC1925`, `HEC2258`), esa etiqueta manda y el conflicto se documenta.

## 4. Fuentes candidatas (verificadas por búsqueda web, no integradas)

| Fuente | URL | Estado | Potencial | Motivo de no integrar todavía |
|---|---|---|---|---|
| Casas Oasis | `https://casasoasis.com/es/venta/viviendas` | accesible | datos estructurados con habitaciones, baños, fotos y fechas | sin extractor implementado ni estructura validada |
| Busca Tu Choza | `https://buscatuchoza.com/` | accesible | detalle más completo en algunos anuncios (habitaciones, baños, m²) | sin extractor implementado |
| HousesCuba | `https://www.housescuba.com/` | accesible | — | orientada a alojamientos turísticos, no a venta inmobiliaria general |

## 5. Fuentes excluidas por política

- **Facebook y Telegram**: no se automatiza su captura. Solo aportan evidencia manual y la encuesta anónima.
- **Casas Oasis, Busca Tu Choza y HousesCuba**: fuera del alcance temporal del proyecto; se documentan como líneas futuras de ampliación.

## Conclusión para el proyecto

1. Mantener **Revolico** como fuente principal (volumen alto, canal informal), con la ficha individual como vía de recuperación de metadatos.
2. Usar **Cubisima** como fuente estructurada complementaria (más variables, único bloque masivo en CUC).
3. Usar **HogarEnCuba** como fuente estructurada de precio alto y única con superficie.
4. Antes de mezclar fuentes, estandarizar **moneda, ubicación, tipo de vivienda y fechas**; en este proyecto eso se resuelve con columnas paralelas (`*_original` frente a `*_analisis`) y con la homologación de municipios de `ubicaciones.py`.

El análisis vigente se genera desde el maestro `outputs/integracion/dataset_maestro_20261019_223630.csv` (1.532 filas). Las salidas analíticas se guardan en carpetas fechadas y no sustituyen resultados históricos. El informe final queda pendiente de autorización expresa.
