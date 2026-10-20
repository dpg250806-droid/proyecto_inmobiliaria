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

El maestro local más reciente es `outputs/integracion/dataset_maestro_20261018_225829.csv`, con 1.560 filas: 775 Revolico, 597 Cubisima y 188 HogarEnCuba (6 anuncios no residenciales apartados; ver más abajo). El CSV original de Cubisima y los maestros anteriores continúan sin modificaciones. El análisis preliminar basado en ese maestro está en `outputs/preguntas/preguntas_resueltas_20261018_231919.md`; no es el informe final, pendiente de las entrevistas.

### Columnas de precio y revisión del maestro

El maestro distingue el campo publicado del precio que se analiza; nada se corrige ni se borra:

| Columna | Tipo | Contenido y uso |
|:---------|:-----|:----------------|
| `precio_original`, `moneda` | numerico / categorica | Campo publicado por la fuente. Se conserva sin corregir y mide la cobertura de cada canal. |
| `precio_sospechoso` | booleano | Marca importes que no deben analizarse tal cual: moneda contradicha por la fuente, importe 1, veredicto manual excluyente, etc. 154 marcas en la base vigente. |
| `veredicto_revision` | categorica | Veredicto de la revisión de precios (listas `precios_bajos.csv` y `precios_ausentes.csv`): `error`, `producto`, `permuta`, `despublicado`, `no_verificable`, `otro`, `precio_recuperado`, `sin_precio_en_texto`, `solo_coincide_con_publicado`, `anuncio_no_disponible`, `consulta_fallida`, `no_consultado_sin_red`, `ambiguo`, `moneda_ambigua`, `moneda_sin_tasa`, `cup_requiere_validacion`, `valor_improbable`, `solo_coincidencias_tipograficas`. Solo los veredictos excluyentes (`alquiler`, `despublicado`, `error`, `no_verificable`, `otro`, `permuta`, `producto`) marcan `precio_sospechoso`; el resto deja constancia sin excluir. Si dos listas informan del mismo anuncio, gana la primera (`precios_bajos.csv`, la revisión manual original). Vacío si el anuncio no fue revisado. |
| `precio_reextraido` | numerico | Precio verificado en la descripción o el título del anuncio por revisión manual (25 anuncios: 12 de `precios_bajos.csv` y 13 de la búsqueda de precios ausentes). Vacío cuando no hay precio verificable. |
| `moneda_reextraida` | categorica | Moneda declarada en esa misma evidencia. |
| `evidencia_precio` | texto | Cita literal de la evidencia usada en la reextracción; permite reabrir cada caso. |
| `precio_analisis` | numerico | Precio que usan conversión, comparativo, segmentación, clustering y preguntas. Reglas: reextracción verificada primero; después el campo publicado si no está marcado como sospechoso y tiene moneda; si no, vacío (no se imputa). |
| `moneda_analisis` | categorica | Moneda asociada a `precio_analisis`. |
| `origen_precio` | categorica | `reextraccion_manual` (25), `campo_publicado` (1406) o `excluido` (129). |

### Revisiones de precios y anuncios no residenciales

`aplicar_veredictos_revision()` aplica por defecto dos listas versionadas en `revision_manual/`:

- `precios_bajos.csv`: revisión uno a uno de los 59 precios inferiores a 100 contra la página del anuncio.
- `precios_ausentes.csv`: la salida de `revisar_precios_ausentes.py`, que busca precio en título, descripción y página de cada anuncio sin `precio_analisis` y deja un veredicto por anuncio. Las reglas son conservadoras: hace falta una moneda explícita (`$` solo no basta, puede ser USD o CUC), 7 o más dígitos sin separador se tratan como posible teléfono, dos importes distintos no se resuelven solos, y CUP/MLC quedan para validación manual. Una reejecución conserva lo decidido en corridas anteriores.

Lo que no se pudo resolver queda en `outputs/validacion/precios_pendientes_<fecha>.csv/.md` (129 anuncios el 18/10/2026) para revisión manual, con el motivo y las citas. Los anuncios que no son vivienda en venta (veredictos `producto`, `permuta`, `otro` y `alquiler`) se apartan del maestro por `excluir_no_residenciales()` y quedan documentados en `outputs/integracion/anuncios_no_residenciales_<fecha>.csv`; no se borra ninguna fuente original.

El campo `tipo_vivienda` de Revolico se clasifica con palabras clave sobre el título completo (`clasificar_tipo_vivienda()`, misma precedencia que `limpiar_revolico.py`: penthouse > casa > apartamento/apto) porque el CSV de origen no trae ese campo: antes se usaba la primera palabra del título, lo que metía precios y teléfonos como tipos (734 filas). Lo no reconocido queda `no_clasificado` (138 filas) y, si no hay título, no se inventa ningún tipo.

### Entrevistas anónimas (`procesar_entrevistas.py`)

El export anónimo del formulario (CSV o XLSX) se procesa sin persistir jamás metadatos personales: cualquier columna de correo, nombre o teléfono se descarta antes de escribir. Las respuestas se anonimizan como `entrevista_id` E01..E0N y cada fila conserva `fecha_respuesta` (ISO cuando se puede parsear) más una columna por pregunta (`relacion`, `municipio`, `evolucion_precios`, `factores_precio`, `influencia_tasas`, `refleja_precio`, `influencia_migracion`, `factor_dominante`, `reduccion_precio`, `canales`). La salida queda en `outputs/entrevistas/entrevistas_codificadas_<fecha>.csv` con códigos calculados sobre el texto completo de cada respuesta (minúsculas sin tildes, búsqueda por subcadena):

| Código | Criterio |
|---|---|
| `C1_necesidad_economica` | dinero, necesidad, urgencia o miseria |
| `C2_migracion` | migra*, travesía, Nicaragua |
| `C3_moneda_tasa` | USD, CUP, tasas o moneda |
| `C4_canal_venta` | Telegram, WhatsApp, Facebook o grupo |
| `C5_precio_alto` | caro, carísimo, regalo o valor |
| `C6_caracteristicas` | m2, metro, baño(s) o piscina |
| `C7_municipio` | cualquier municipio de La Habana en el texto |

`A1_cita` guarda los primeros 220 caracteres como cita ilustrativa y el `resumen_entrevistas_<fecha>.md` reproduce frecuencias, relación/municipio y las respuestas literales del factor dominante y de la migración. Los códigos son heurísticas de frecuencia para organizar el discurso (p. ej. «valor» aparece también al hablar del valor real): no sustituyen la lectura manual ni prueban causalidad.

### Metadatos de la página del anuncio de Revolico

La tarjeta del listado guardado (`paginas_revolico/`) solo contiene imagen, precio, título y enlace: **el municipio y la fecha no están en el HTML de listado**. Cuando existen, viven en la página individual del anuncio, dentro de `__NEXT_DATA__` → `props.pageProps.__APOLLO_STATE__`. `extraer_metadatos_revolico.py` consulta cada URL del maestro (con reintentos y espera) y guarda la evidencia en `outputs/metadatos_revolico/metadatos_revolico_<marca>.csv`; la extracción es reanudable con `--reanudar` y registra el estado de cada anuncio, incluidos los despublicados o borrados.

| Columna | Tipo | Contenido y uso |
|:---------|:-----|:----------------|
| `municipio_reextraido` | texto | Municipio leído de la página del anuncio. Procedencia en `metodo_municipio`: `apollo` (campo estructurado `MunicipalityType:<id>`) o `texto_titulo_o_descripcion` (búsqueda por palabra entera en el texto, solo si coincide un único municipio; varias coincidencias se descartan). Vacío si la página no respondió o no hay municipio verificable. |
| `metodo_municipio` | categorica | De dónde salió `municipio_reextraido`. |
| `fecha_reextraida` | fecha ISO | `updatedOnByUser`, la fecha exacta que el sitio muestra como "hace X días". **Es la fecha de la última actualización del anuncio, no necesariamente la de creación.** No se mezcla con `fecha_publicacion` de las otras fuentes. |
| `estado_anuncio` | categorica | `publicado`, `despublicado` o `anuncio_inexistente_<codigo>`. Registra la sesión de disponibilidad al momento de la consulta; no descarta el anuncio. |
| `vendido` | booleano | `isSold` del anuncio. |
| `evidencia_metadatos` | texto | Archivo de metadatos y URL de origen, para reabrir cada caso. |
| `ubicacion_analisis` | texto | Ubicación que usan las medianas por municipio. Reglas: municipio verificado en la página primero; después `ubicacion_raw`; vacío si ambos faltan. No se imputa. |
| `origen_ubicacion` | categorica | `pagina_anuncio`, `campo_publicado` o `sin_dato`. |

### Habitaciones, baños y disponibilidad de Revolico

La tarjeta del listado solo aporta el título, y el título casi nunca menciona baños. `extraer_detalle_anuncios_revolico.py` busca la cantidad escrita por el anunciante en la **descripción**, el **título** y el **enlace (slug)** de cada anuncio, con patrones conservadores: dígitos ("3 cuartos", "4 hab", "2 banos"), palabras ("un cuarto", "dos banos", hasta diez), notación habanera ("apto 2/4" = 2 dormitorios) y fracciones de baño ("medio bano" y "N banos y medio" suman 0.5). Reglas: primera aparición explícita gana; si el mismo texto menciona dos cantidades distintas, ambas quedan en la evidencia y el conflicto se marca sin resolver; si no hay mención, no se rellena nada. La cadena al integrar el maestro es descripción primero y, si la descripción no menciona la cantidad, el título del propio anuncio (p. ej. `Apto 1/4` = 1 dormitorio); después entran el campo publicado y el slug del enlace. La salida es `outputs/metadatos_revolico/detalle_anuncios_revolico_<marca>.csv` y se aplica con `aplicar_detalle_anuncios()`.

| Columna | Tipo | Contenido y uso |
|:---------|:-----|:----------------|
| `habitaciones_reextraido` | numerico | Habitaciones leídas de la descripción del anuncio; si la descripción no las menciona, del título del anuncio. |
| `banos_reextraido` | numerico | Baños leídos de la descripción del anuncio; si la descripción no los menciona, del título del anuncio. |
| `habitaciones_slug` | numerico | Habitaciones escritas en el enlace (slug), solo cuando no hay descripción. |
| `banos_slug` | numerico | Baños escritos en el enlace (slug). |
| `evidencia_detalle` | texto | Fragmento literal que justifica el valor extraído (p. ej. `habitaciones='4 cuartos'`, o `habitaciones_titulo='1/4'` cuando el valor viene del título). |
| `conflicto_detalle` | texto | Marcado cuando título y descripción, o el propio texto, ofrecen cantidades distintas. No se resuelve: se conserva la primera aparición. |
| `habitaciones_analisis` | numerico | Habitaciones que usan segmentación, clustering, medianas y gráficos. Reglas: descripción/título primero; después el campo publicado; después el slug; vacío si nada lo dice. No se imputa. |
| `banos_analisis` | numerico | Baños con la misma regla. |
| `origen_habitaciones` | categorica | `descripcion_o_titulo`, `campo_publicado`, `slug` o vacío. |
| `origen_banos` | categorica | Igual que el anterior, para baños. |
| `fecha_ultima_disponibilidad` | fecha | Para anuncios no publicados: fecha del listado guardado donde aún aparecían (timestamp de Cloudflare del HTML). |
| `ventana_despublicacion` | texto | Intervalo `AAAA-MM-DD a AAAA-MM-DD` dentro del cual ocurrió la desaparición: desde el listado guardado hasta la consulta que devolvió el error. Es un límite con evidencia, no una fecha exacta: la página borrada no conserva fecha. |
| `justificacion_disponibilidad` | texto | Explicación legible de por qué el anuncio sigue en el dataset pese a no estar accesible. |

La función `detalle_analisis()` de `precio_moneda.py` implementa la regla de precedencia en un solo sitio y también funciona con maestros antiguos sin columnas de reextracción (cae al campo publicado). **Cobertura honesta (Revolico, 775 anuncios):** habitaciones 535 (69%) y baños 288 (37%). El techo lo fija el propio texto: 156 anuncios ya no están accesibles y no tienen descripción, y otros anuncios publicados simplemente no mencionan la cantidad. No se imputa nada.

El **m² queda fuera del análisis**: ninguna fuente lo publica de forma sistemática (Revolico 0%, Cubisima 0%, HogarEnCuba ~5%). La columna `superficie_m2` se conserva en el maestro solo como traza de origen; su cobertura se reporta como hallazgo comparativo (los clasificados informales no lo ofrecen), nunca como variable explicativa de precios.

La función `precios_analisis()` de `precio_moneda.py` implementa estas reglas en un solo sitio y también funciona con maestros antiguos que no tienen las columnas nuevas. Los scripts derivados regeneran sus salidas con fecha y hora propias; los resultados antiguos no se sobrescriben.

## Tasas y equivalencias

El registro local de tasas no contiene `cuc_informal_cup` ni `cuc_formal_cup`. La conversión nominal actual es `outputs/conversiones/dataset_maestro_conversion_cuc_nominal_20261018_231830.csv`; usa `--cuc-usd-nominal` bajo la decisión explícita de la usuaria de aplicar 1 CUC = 1 USD como equivalencia nominal, no como tasa de mercado, y solo a anuncios con `fecha_publicacion` posterior a 2021 (los 545 registros CUC publicados van del 17/10/2023 al 12/10/2026; el maestro deja 16 fuera por sospecha y la conversión se aplica a los 529 restantes). El método queda en `metodo_conversion_cuc` y la paridad aplicada en `fx_cuc_usd_nominal`. Se conserva el importe y la moneda originales; no se inventa una tasa CUC/CUP.

Los análisis por precio, zona, habitaciones, canal, segmentación y clustering separan por moneda y excluyen moneda desconocida de las comparaciones de importes. Los resultados antiguos no se regeneran solos al cambiar parsers.

## Archivos locales

`.gitignore` excluye `data/`, `outputs/` y los CSV locales derivados de Revolico/Cubisima para evitar añadir datos o resultados accidentalmente. No se deben borrar ni versionar como parte de esta revisión.