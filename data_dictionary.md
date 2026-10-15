# Diccionario de datos del proyecto inmobiliario (Revolico, La Habana)

Etapa: auditoria inicial. Fecha de documentacion: 2026-10-15.

Los tipos indicados corresponden a la lectura por pandas de los CSV actuales. Las definiciones se basan en el codigo existente y en la auditoria verificada; no se incorporan datos hipoteticos.

## `enlaces_anuncios_revolico.csv`

780 filas x 4 columnas. Sin valores ausentes en las cuatro columnas. 0 URLs duplicadas.

| Columna | Tipo | Descripcion | Limitaciones |
|---|---|---|---|
| `titulo` | texto | Titulo visible de la tarjeta del anuncio. | Puede contener precio, moneda, ubicacion y detalles en formato libre. |
| `texto_tarjeta` | texto largo | Texto plano del contenedor obtenido al subir dos niveles desde el enlace. | Contenedor compartido: puede mezclar varios anuncios. No usar como feature final. |
| `url` | texto/URL | Enlace individual del anuncio en Revolico. | Identificador principal; no duplicado en el corpus actual. |
| `pagina_origen` | texto | Nombre del archivo HTML del que se extrajo la tarjeta. | Trazabilidad parcial; depende de archivos HTML no versionados. |

## `anuncios_revolico_procesados.csv`

780 filas x 9 columnas. Resultado de `procesar_anuncios_revolico.py`.

| Columna | Tipo | Descripcion | Ausencias verificadas |
|---|---|---|---|
| `titulo` | texto | Titulo del anuncio. | 0 |
| `texto_tarjeta` | texto largo | Texto del contenedor extraido. | 0 |
| `url` | texto/URL | Enlace del anuncio. | 0 |
| `pagina_origen` | texto | Archivo HTML de origen. | 0 |
| `precio` | numerico | Numero extraido del inicio del titulo, sin decimales ni separadores. | 46 |
| `moneda` | categorica | Moneda detectada en el titulo: USD, CUP en este corpus. | 46 |
| `sirve_proyecto` | categorica | Clasificacion automatica: SI, REVISAR o NO. | 0 |
| `municipio` | texto | Municipio de La Habana detectado en el titulo por lista cerrada. | 491 |
| `habitaciones` | numerico | Numero de habitaciones/cuartos detectado en el titulo. | 710 |

## `viviendas_revolico_candidatas.csv`

763 filas x 9 columnas. Subconjunto con `sirve_proyecto == SI`.

Mismas columnas que `anuncios_revolico_procesados.csv`. Ausencias verificadas en candidatas:
- `precio`: 40
- `moneda`: 40
- `municipio`: 480
- `habitaciones`: 695

## `anuncios_revolico_revisar.csv`

10 filas x 9 columnas. Subconjunto con `sirve_proyecto == REVISAR`.

Mismas columnas que el dataset procesado. Ausencias verificadas:
- `precio`: 2
- `moneda`: 2
- `municipio`: 7
- `habitaciones`: 9

## `anuncios_revolico_excluidos.csv`

7 filas x 9 columnas. Subconjunto con `sirve_proyecto == NO`.

Mismas columnas que el dataset procesado. Ausencias verificadas:
- `precio`: 4
- `moneda`: 4
- `municipio`: 4
- `habitaciones`: 6

## `datos_revolico_json.csv`

25 filas x 11 columnas. Extraido por `extraer_datos_revolico.py` desde `__NEXT_DATA__` de las paginas HTML.

| Columna | Tipo | Descripcion | Limitaciones verificadas |
|---|---|---|---|
| `id` | entero/texto | Identificador del anuncio en el JSON. | El mismo conjunto de 25 IDs aparece en las 8 paginas. |
| `titulo` | texto | Titulo del anuncio en JSON. | Corresponden a productos diversos, no exclusivamente viviendas. |
| `precio` | numerico | Precio en JSON. | 6 ausentes; no validado para poblacion vivienda. |
| `moneda` | texto | Moneda en JSON. | 6 ausentes; solo USD en registros no nulos. |
| `municipio_id` | entero | ID numerico de municipio en JSON. | No mapeado a nombre del municipio en el dataset. |
| `provincia_id` | entero | ID numerico de provincia en JSON. | Siempre 1 en los registros auditados. |
| `fecha_publicacion` | fecha | Campo esperado por el extractor. | 25 ausencias; el JSON usa `updatedOnToOrder`, no `publishedOnOrder`. |
| `promocionado` | booleano | Indica si el anuncio esta promocionado. | Solo `False` en los registros auditados. |
| `cantidad_imagenes` | entero | Numero de imagenes en el JSON. | Derivado del mismo subconjunto no vivienda. |
| `url` | texto/URL | Enlace individual. | 0 ausencias. |
| `archivo_origen` | texto | Archivo HTML de origen. | Todos los registros corresponden a `revolico_pagina_8.html`. |

## CSV pequenos de ejemplo

### `viviendas.csv`
3 filas x 3 columnas (`municipio`, `precio`, `habitaciones`). Generado por `analisis_inmobiliario.py` con datos inventados. No representa anuncios reales.

### `viviendas_limpias.csv`
2 filas x 3 columnas (`municipio`, `precio`, `habitaciones`). Generado por `analisis_inmobiliario.py` con datos inventados. No representa anuncios reales.

## Archivo no integrado: Cubisima

Los siguientes archivos existen localmente sin trackear en Git y no se han integrado en esta etapa:
- `scraper_cubisima.py`
- `viviendas_cubisima.csv`
- `explorar_cubisima.py`
- `revisar_cubisima.py`
- `auditar_cubisima.py`

`viviendas_cubisima.csv` tiene 625 filas x 19 columnas, pero no se uso como fuente principal ni se mezclo con Revolico en esta etapa.