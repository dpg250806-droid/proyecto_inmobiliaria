# Fuentes cubanas de viviendas: estado de verificación

**Auditoría técnica:** 21/10/2026 · **Corte de datos:** 19/10/2026.

Resumen de la decisión de fuentes: **Revolico** aporta volumen y es el clasificado informal; **Cubisima** aporta estructura y es la única fuente masiva en CUC; **HogarEnCuba** aporta fichas estructuradas de precio más alto. Las demás fuentes quedan como candidatas futuras y no entran en el análisis actual.

Esta auditoría fue completamente offline: los estados de acceso web describen las capturas documentadas y no se revalidaron contra los sitios.

## 1. Revolico (fuente principal, informal)

- URL base usada: `https://www.revolico.com/search?category=inmobiliaria&subcategory=inmobiliaria-casas&province=la-habana`
- Estado online: **bloqueado por Cloudflare/anti-bot** para scraping automático (HTTP 403; Playwright y Selenium reciben la página "Un momento..."). Solución operativa: guardar las páginas HTML y procesarlas localmente.
- Datos actuales: 780 anuncios únicos extraídos de 8 páginas HTML locales; **748** entran al maestro vigente.
- La **página individual de cada anuncio sí respondía** (hasta el 18/10/2026): de ahí se extraen municipio, fecha (`updatedOnByUser`) y descripción completa, y con el texto se reconstruyen habitaciones y baños.
- Fortaleza: gran volumen y precios en USD.
- Limitaciones: municipio ausente en el campo publicado (286/748; 38,2 %), habitaciones en 69/748 (9,2 %), baños en 0 % y fecha en 0 %; superficie nunca. 153 de 748 anuncios ya no son accesibles (80 despublicados, 73 eliminados).
- **Prueba de actualización del 22/10/2026**: el refresco de disponibilidad sobre las fichas individuales devolvió **HTTP 403 (desafío de Cloudflare) en las 78 peticiones alcanzadas** y se abortó sin forzar el sitio; las cabeceras de navegador completo no lo eluden. Consecuencia: el estado verificable de disponibilidad sigue siendo el del snapshot del 18/10/2026 y no se puede reconfirmar online cuándo desapareció cada anuncio. Las 16 fichas ya marcadas como no disponibles sí se re-verificaron ese mismo día y siguen inaccesibles.

## 2. Cubisima (fuente estructurada complementaria)

- URL base usada: `https://www.cubisima.com/casas/anuncios/la-habana/`
- Última ejecución confirmada por la usuaria: **27 páginas con HTTP 200 y 625 anuncios únicos**. Esta auditoría no hizo peticiones de red ni volvió a comprobar la disponibilidad actual.
- Prueba limitada del 22/10/2026: HTTP 200; 24 anuncios únicos en la primera página; el HTML indica 25 páginas. La captura completa no se ejecutó para evitar recargar el sitio. La CLI ahora distingue entre páginas detectadas y las limitadas por `--max-pages`.
- Snapshot local `viviendas_cubisima.csv`: 625 filas; **585** entran al maestro vigente. De las filas integradas, 535 conservan precio y moneda publicada CUC; 530 tienen precio utilizable para análisis.
- Campos observados: tipo, zona, habitaciones, baños, precio, moneda, fecha y seis características auxiliares (garaje, piscina, terraza, patio, balcón, jardín).
- Fechas en `dd/mm/yyyy` entre 29/09/2023 y 25/09/2026; ninguna posterior al corte.
- Fortaleza: más variables estructuradas que Revolico y única fuente masiva en CUC.
- Limitaciones: la zona mezcla municipios y barrios (98/585 fichas coinciden con un municipio de La Habana); no publica superficie; 50 fichas integradas sin moneda publicada y 55 sin precio de análisis; no hay tasa CUC/CUP verificada, por lo que la conversión a USD usa una **paridad nominal declarada** (1 CUC = 1 USD), no una tasa de mercado.

## 3. HogarEnCuba (fuente estructurada complementaria)

- URL observada: `https://hogarencuba.com/ventas/la-habana`
- Estado: página accesible; captura reproducible con `scraper_hogarencuba.py` (10/10 páginas, 0 fallidas) → **188 fichas** en el snapshot vigente; **183** entran al maestro.
- Prueba limitada del 22/10/2026: una página con 13 fichas de listado, 13 fichas de detalle consultadas y 0 fallidas. Como se limitó intencionalmente a 1 de 10 páginas, el CSV temporal quedó marcado correctamente como incompleto; no representa un snapshot para análisis.
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

El maestro vigente verificado es `outputs/integracion/dataset_maestro_20261020_234716.csv` (1.516 filas). Las salidas analíticas existentes corresponden a ejecuciones fechadas; no se regeneraron en esta auditoría para preservar los outputs locales. El informe final queda pendiente de autorización expresa.
