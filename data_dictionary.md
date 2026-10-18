# Diccionario de datos del proyecto inmobiliario (Revolico, La Habana)

Etapa: auditoria local y correccion de parseo de moneda. Actualizado: 2026-10-17.

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
3 filas x 3 columnas (`municipio`, `precio`, `habitaciones`). Generado por `analisis_inmobiliario.py` (script de ejemplo retirado el 2026-10-18) con datos inventados. No representa anuncios reales y no interviene en ningun analisis.

### `viviendas_limpias.csv`
2 filas x 3 columnas (`municipio`, `precio`, `habitaciones`). Generado por `analisis_inmobiliario.py` (script de ejemplo retirado el 2026-10-18) con datos inventados. No representa anuncios reales y no interviene en ningun analisis.

## Cubisima (snapshot local)

`viviendas_cubisima.csv` contiene 625 filas y 19 columnas. Se usa como entrada local para Cubisima y sus registros ya aparecen en los maestros locales; por tanto, no es correcto describir esta fuente como “no integrada”.

| Campo | Estado observado en el CSV local |
|---|---|
| `precio` | 571 números detectados en texto con símbolo `€`; 54 ausentes porque la tarjeta dice “Sin precio”. |
| `moneda` | Los 571 con precio están guardados como `EUR`; sin precio queda vacía. |
| `url` | En los 571 con precio, el slug contiene `-<mismo importe>-cuc-`; el parser actual lo usa para clasificar CUC cuando coincide exactamente con el importe mostrado. |
| `texto_tarjeta` | Evidencia original preservada por fila; debe seguir tratándose como texto fuente, no como feature aislada. |

El archivo original guardado sigue intacto. La copia auditada `outputs/cubisima/viviendas_cubisima_reprocesada_20261017_221516.csv` contiene los 571 casos como CUC y añade los campos anteriores para auditoría. `integrar_fuentes.py` utilizó esa copia para crear `outputs/integracion/dataset_maestro_20261017_221530.csv`; el snapshot anterior no fue sobrescrito.

## HogarEnCuba y datos maestros locales

El snapshot histórico `outputs/hogarencuba/viviendas_hogarencuba_revisada_20261017_014824.csv` contiene 155 fichas y se conserva intacto. Una comparación ampliada encontró 14 fichas con precio o moneda discordantes; se consultaron las 14 URLs y todas respondieron HTTP 200. Para esas fichas, el precio actual se verificó contra la oferta JSON-LD cuyo `sku`/`identifier` coincide con el ID local. Si el cuerpo del propio anuncio declara `PRECIO EN EUR`, esa etiqueta es la autoridad para la moneda aunque el título o JSON-LD indiquen USD. Se añadieron `precio_metodo_extraccion` y `precio_evidencia` para dejar la procedencia auditable.

El snapshot `outputs/hogarencuba/viviendas_hogarencuba_revalidada_20261017_232654.csv` conserva las 155 filas del origen y revalida en vivo 14 discrepancias; las otras 141 se conservan sin recaptura y tienen estado explícito `sin_discrepancia_en_evidencia_local`. El origen histórico permanece intacto. Después se completó una captura nueva en `outputs/hogarencuba/viviendas_hogarencuba_20261017_234325.csv`: 188 URLs únicas, 10 de 10 páginas y 0 fichas fallidas. Los precios llevan `precio_metodo_extraccion` y `precio_evidencia`; los 14 IDs discrepantes anteriores aparecen con el parser actual. HEC2258 se registra como EUR por la etiqueta expresa `PRECIO EN EUR`; los otros 13 casos de ese grupo tienen moneda USD del JSON-LD asociado al ID exacto.

El maestro local más reciente es `outputs/integracion/dataset_maestro_20261018_151710.csv`, con 1.566 filas: 780 Revolico, 598 Cubisima y 188 HogarEnCuba. El CSV original de Cubisima y los maestros anteriores continúan sin modificaciones. El análisis preliminar basado en ese maestro está en `outputs/preguntas/preguntas_resueltas_20261018_154323.md`; no es el informe final, pendiente de las entrevistas.

### Columnas de precio y revisión del maestro

El maestro distingue el campo publicado del precio que se analiza; nada se corrige ni se borra:

| Columna | Tipo | Contenido y uso |
|:---------|:-----|:----------------|
| `precio_original`, `moneda` | numerico / categorica | Campo publicado por la fuente. Se conserva sin corregir y mide la cobertura de cada canal. |
| `precio_sospechoso` | booleano | Marca importes que no deben analizarse tal cual: moneda contradicha por la fuente, importe 1, veredicto manual excluyente, etc. 160 marcas en la base vigente. |
| `veredicto_revision` | categorica | Veredicto de la revisión manual de precios bajos: `error`, `producto`, `permuta`, `despublicado`, `no_verificable`, `otro`. Vacío si el anuncio no fue revisado. |
| `precio_reextraido` | numerico | Precio verificado en la descripción o el título del anuncio durante la revisión manual (12 anuncios). Vacío cuando no hay precio verificable. |
| `moneda_reextraida` | categorica | Moneda declarada en esa misma evidencia. |
| `evidencia_precio` | texto | Cita literal de la evidencia usada en la reextracción; permite reabrir cada caso. |
| `precio_analisis` | numerico | Precio que usan conversión, comparativo, segmentación, clustering y preguntas. Reglas: reextracción verificada primero; después el campo publicado si no está marcado como sospechoso y tiene moneda; si no, vacío (no se imputa). |
| `moneda_analisis` | categorica | Moneda asociada a `precio_analisis`. |
| `origen_precio` | categorica | `reextraccion_manual` (12), `campo_publicado` (1406) o `excluido` (148). |

La función `precios_analisis()` de `precio_moneda.py` implementa estas reglas en un solo sitio y también funciona con maestros antiguos que no tienen las columnas nuevas. Los scripts derivados regeneran sus salidas con fecha y hora propias; los resultados antiguos no se sobrescriben.

## Tasas y equivalencias

El registro local de tasas no contiene `cuc_informal_cup` ni `cuc_formal_cup`. La conversión nominal actual es `outputs/conversiones/dataset_maestro_conversion_cuc_nominal_20261018_002424.csv`; usa `--cuc-usd-nominal` bajo la decisión explícita de la usuaria de aplicar 1 CUC = 1 USD como equivalencia nominal, no como tasa de mercado, y solo a anuncios con `fecha_publicacion` posterior a 2021 (los 546 registros CUC van del 17/10/2023 al 12/10/2026). De ellos, 540 se convirtieron y 6 sospechosos quedaron sin conversión; el método queda en `metodo_conversion_cuc` y la paridad aplicada en `fx_cuc_usd_nominal`. Se conserva el importe y la moneda originales; no se inventa una tasa CUC/CUP.

Los análisis por precio, zona, habitaciones, canal, segmentación y clustering separan por moneda y excluyen moneda desconocida de las comparaciones de importes. Los resultados antiguos no se regeneran solos al cambiar parsers.

## Archivos locales

`.gitignore` excluye `data/`, `outputs/` y los CSV locales derivados de Revolico/Cubisima para evitar añadir datos o resultados accidentalmente. No se deben borrar ni versionar como parte de esta revisión.