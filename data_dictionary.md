# Diccionario de datos del proyecto inmobiliario (La Habana)

**Alcance:** Revolico, Cubisima y HogarEnCuba. **Corte de datos:** 19/10/2026. **Actualizado:** 20/10/2026.

Los tipos indicados corresponden a la lectura por `pandas` de los CSV actuales. Las definiciones se basan en el código existente y en la auditoría verificada: **no se incorporan datos hipotéticos**. Ninguna fuente original se modifica en ningún paso del pipeline.

## 0. Convenciones generales

| Convención | Significado |
|---|---|
| Celda vacía | El dato **no existe** en la fuente o no se pudo extraer. Nunca se rellena con ceros, medias ni valores plausibles. |
| Marca de sospecha (`precio_sospechoso`) | El dato existe pero **no debe analizarse tal cual**. |
| `veredicto_revision` | Resultado de la revisión manual: el dato es **inexistente**, **no extraído** o **pendiente de revisión manual**. |
| `origen_*` | Procedencia exacta de cada campo de análisis, para poder auditar y revertir. |
| `evidencia_*` | Cita literal que justifica el valor asignado. |
| Fechas | Se guardan en ISO (`AAAA-MM-DD`) cuando son exactas. Las fechas relativas de HogarEnCuba ("hace 2 años") se convierten a fecha aproximada y se marcan como tales. Las fechas de Cubisima vienen en `dd/mm/yyyy` y se parsean con `dayfirst`; nunca se comparan como texto. |
| Unidades | Los importes van en su moneda original, sin conversión dentro de la tabla. La conversión vive en `outputs/conversiones/` con tasa, fecha y método. |

## 1. `enlaces_anuncios_revolico.csv`

780 filas × 4 columnas. Sin valores ausentes. 0 URLs duplicadas. Es la salida del listado guardado (`paginas_revolico/`), no una extracción de la web.

| Columna | Tipo | Descripción | Limitaciones |
|---|---|---|---|
| `titulo` | texto | Título visible de la tarjeta del anuncio. | Puede contener precio, moneda, ubicación y detalles en formato libre. |
| `texto_tarjeta` | texto largo | Texto plano del contenedor, obtenido al subir dos niveles desde el enlace. | Contenedor compartido: puede mezclar varios anuncios. **No usar como feature individual.** |
| `url` | texto/URL | Enlace individual del anuncio en Revolico. | Identificador principal; no duplicado en el corpus actual. |
| `pagina_origen` | texto | Nombre del archivo HTML del que se extrajo la tarjeta. | Trazabilidad parcial: depende de HTML no versionado. |

## 2. `anuncios_revolico_procesados.csv`

780 filas × 9 columnas. Resultado de `procesar_anuncios_revolico.py`.

| Columna | Tipo | Descripción | Ausencias verificadas |
|---|---|---|---|
| `titulo` | texto | Título del anuncio. | 0 |
| `texto_tarjeta` | texto largo | Texto del contenedor extraído. | 0 |
| `url` | texto/URL | Enlace del anuncio. | 0 |
| `pagina_origen` | texto | Archivo HTML de origen. | 0 |
| `precio` | numérico | Número extraído del inicio del título, sin decimales ni separadores. | 46 |
| `moneda` | categórica | Moneda detectada en el título (USD, CUP, CUC en este corpus). | 46 |
| `sirve_proyecto` | categórica | Clasificación automática: `SI`, `REVISAR` o `NO`. | 0 |
| `municipio` | texto | Municipio de La Habana detectado en el título por lista cerrada. | 491 |
| `habitaciones` | numérico | Número de habitaciones o cuartos detectado en el título. | 710 |

## 3. `viviendas_revolico_candidatas.csv`

763 filas × 9 columnas. Subconjunto con `sirve_proyecto == SI`. Mismas columnas que el dataset procesado. Ausencias: `precio` 40, `moneda` 40, `municipio` 480, `habitaciones` 695.

## 4. `anuncios_revolico_revisar.csv`

10 filas × 9 columnas. Subconjunto con `sirve_proyecto == REVISAR`. Ausencias: `precio` 2, `moneda` 2, `municipio` 7, `habitaciones` 9.

## 5. `anuncios_revolico_excluidos.csv`

7 filas × 9 columnas. Subconjunto con `sirve_proyecto == NO`. Ausencias: `precio` 4, `moneda` 4, `municipio` 4, `habitaciones` 6.

## 6. `datos_revolico_json.csv`

25 filas × 11 columnas. Extracción **diagnóstica** del JSON-LD (`__NEXT_DATA__`) de las páginas HTML, hecha con `extraer_datos_revolico.py`. **No es una fuente de precio** y no interviene en el análisis: se conserva para documentar qué expone el sitio.

| Columna | Tipo | Descripción | Limitaciones verificadas |
|---|---|---|---|
| `id` | entero/texto | Identificador del anuncio en el JSON. | El mismo conjunto de 25 IDs aparece en las 8 páginas. |
| `titulo` | texto | Título del anuncio en JSON. | Corresponden a productos diversos, no solo vivienda. |
| `precio` | numérico | Precio en JSON. | 6 ausentes; no validado para población vivienda. |
| `moneda` | texto | Moneda en JSON. | 6 ausentes; solo USD en los registros no nulos. |
| `municipio_id` | entero | ID numérico de municipio en JSON. | No mapeado a nombre de municipio en el dataset. |
| `provincia_id` | entero | ID numérico de provincia en JSON. | Siempre 1 en los registros auditados. |
| `fecha_publicacion` | fecha | Campo esperado por el extractor. | 25 ausencias: el JSON usa `updatedOnToOrder`, no `publishedOnOrder`. |
| `promocionado` | booleano | Indica si el anuncio está promocionado. | Solo `False` en los registros auditados. |
| `cantidad_imagenes` | entero | Número de imágenes del anuncio. | Derivado del mismo subconjunto no vivienda. |
| `url` | texto/URL | Enlace individual. | 0 ausencias. |
| `archivo_origen` | texto | Archivo HTML de origen. | Todos los registros corresponden a `revolico_pagina_8.html`. |

> Se eliminaron los CSV de ejemplo `viviendas.csv`, `viviendas_limpias.csv` y `anuncio.json`: eran fixtures inventados de un script de demostración y podían confundirse con datos reales.

## 7. Cubisima (snapshot local)

`viviendas_cubisima.csv` contiene 625 filas × 19 columnas (`fuente, titulo, tipo, zona, habitaciones, banos, precio, moneda, moneda_original, fecha, garaje, piscina, terraza, patio, balcon, jardin, url, pagina_origen, texto_tarjeta`). Es la entrada local de la fuente y no se versiona en Git.

| Campo | Estado observado en el CSV local |
|---|---|
| `precio` | 571 importes detectados en texto con símbolo `€`; 54 ausentes porque la tarjeta dice "Sin precio". |
| `moneda` | Los 571 con precio se guardan como `EUR` (el símbolo del sitio); el slug permite reclasificarlos como CUC cuando el importe coincide con el mostrado. |
| `url` | En los 571 con precio, el slug contiene `-<importe>-cuc-`. |
| `fecha` | Formato `dd/mm/yyyy`; 1 ausencia. Rango 17/10/2023 a 12/10/2026, ninguna fecha posterior al corte. |
| `zona` | Mezcla municipios y barrios (Siboney, Miramar, Vedado). Solo 100 de las 594 fichas del maestro coinciden con un municipio de La Habana. |
| `garaje`, `piscina`, `terraza`, `patio`, `balcon`, `jardin` | Única fuente que publica características auxiliares de forma sistemática. La ausencia equivale a "no declarado", no a "no existe". |
| `texto_tarjeta` | Evidencia original por fila: se trata como texto fuente, nunca como feature aislada. |

El archivo original guardado sigue intacto; `reprocesar_cubisima.py` genera una copia corregida (`outputs/cubisima/viviendas_cubisima_reprocesada_*.csv`) que es la que integra el maestro.

## 8. HogarEnCuba (snapshots)

- `outputs/hogarencuba/viviendas_hogarencuba_revisada_20261018_000535.csv` (188 filas) es el **snapshot válido de integración**: captura integral de 10 de 10 páginas, 0 fichas fallidas.
- Snapshot histórico de 155 fichas (17/10/2026) conservado intacto, con `precio_metodo_extraccion` y `precio_evidencia` para dejar la procedencia auditable.
- Para las 14 fichas con precio o moneda discordantes se consultó la oferta JSON-LD cuyo `sku` coincide con el ID local. **Si el cuerpo del anuncio declara "PRECIO EN EUR", esa etiqueta es la autoridad de la moneda**, aunque el título o el JSON-LD indiquen USD: es el caso de `HEC2258` y `HEC1925`. El conflicto se documenta como limitación.
- `m2` declarado en 9 de 183 fichas; las fechas son relativas ("hace 2 años") y 162 de 183 se convierten a fecha aproximada.

## 9. Maestro integrado

**Archivo vigente:** `outputs/integracion/dataset_maestro_20261020_214356.csv` — 1.523 filas × 59 columnas (Revolico 754, Cubisima 586, HogarEnCuba 183), 0 `id_maestro` duplicados y 0 URLs repetidas. Copia depurada: `outputs/limpieza_integrada/dataset_maestro_depurado_*.csv`.

### 9.1 Identificación y procedencia

| Columna | Tipo | Contenido y uso |
|---|---|---|
| `id_maestro` | texto | Identificador único y estable del anuncio dentro del maestro. |
| `fuente` | categórica | `Revolico`, `Cubisima` o `HogarEnCuba`. |
| `snapshot_origen` | texto | Archivo de origen del que salió la fila. |
| `id_local` | texto | Identificador de la fuente (para Revolico, prefijo corto + URL). |
| `titulo`, `url` | texto | Título y enlace publicados. |
| `tipo_vivienda` | categórica | Clasificación por palabras clave sobre el título completo (`clasificar_tipo_vivienda()`); lo no reconocido queda `no_clasificado`. |
| `canal` | categórica | `Informal - Revolico`, `Estructurado - Cubisima`, `Estructurado - HogarEnCuba`. |
| `agencia_observada`, `calidad_metadatos` | texto / categórica | Señales de intermediario y calidad del anuncio. |

### 9.2 Campos publicados (se conservan sin corregir)

| Columna | Tipo | Contenido y uso |
|---|---|---|
| `precio_original`, `moneda` | numérico / categórica | Campo publicado por la fuente. Mide la cobertura de cada canal; nunca se corrige. |
| `habitaciones`, `banos` | numérico | Campos publicados (Revolico: 69 y 0; Cubisima y HogarEnCuba: 100 %). |
| `superficie_m2` | numérico | Solo HogarEnCuba lo publica (9/183). **Fuera del análisis**: se conserva como traza. |
| `ubicacion_raw` | texto | Ubicación tal como la publica la fuente. |
| `fecha_publicacion` | fecha | Fecha publicada (Cubisima `dd/mm/yyyy` convertida; HogarEnCuba relativa convertida; Revolico sin campo). |
| `fecha_descarga` | fecha | Fecha de la captura. |
| `garaje`, `piscina`, `terraza`, `patio`, `balcon`, `jardin` | categórica | Características auxiliares declaradas (solo Cubisima). |
| `precio_sospechoso` | booleano | Marca importes que no deben analizarse tal cual. **147 marcas** en el maestro vigente: 92 sin moneda publicada y 55 con un problema real de precio o moneda (16 CUC, 5 CUP, 34 USD). |

### 9.3 Revisión manual de precios

| Columna | Tipo | Contenido y uso |
|---|---|---|
| `veredicto_revision` | categórica | Veredicto de la revisión de precios (`revision_manual/precios_bajos.csv`, `revision_manual/precios_bajos_1000.csv` y `revision_manual/precios_ausentes.csv`). Valores vigentes: `sin_precio_en_texto` (69), `no_verificable` (23), `solo_coincide_con_publicado` (15), `precio_recuperado` (14), `error` (13), `anuncio_no_disponible` (8), `despublicado` (8), `cup_requiere_validacion` (5), `ambiguo` (3), `moneda_ambigua` (1), `valor_improbable` (1); vacío en los 1.363 anuncios no revisados. |
| `precio_reextraido`, `moneda_reextraida` | numérico / categórica | Importe y moneda verificados en la descripción o el título (26 anuncios: 13 de la revisión de precios bajos, 13 de la búsqueda de precios ausentes y 1 de la revisión de precios < 1.000, cuyo precio real era "12,500" USD y no los 125 USD publicados). |
| `evidencia_precio` | texto | Cita literal de esa evidencia. |
| `texto_evidencia`, `observacion` | texto | Contexto de la revisión manual. |
| `precio_analisis` | numérico | Precio que usan conversión, comparativo, segmentación, clustering y preguntas. Reglas: reextracción verificada → campo publicado si no está sospechoso y tiene moneda → vacío. **No se imputa.** |
| `moneda_analisis` | categórica | Moneda asociada a `precio_analisis`. |
| `origen_precio` | categórica | `campo_publicado` (1.363), `reextraccion_manual` (26), `excluido` (134). |

### 9.4 Ubicación y municipios

| Columna | Tipo | Contenido y uso |
|---|---|---|
| `municipio_reextraido` | texto | Municipio leído de la página individual del anuncio de Revolico. |
| `metodo_municipio` | categórica | `apollo` (campo estructurado `MunicipityType:<id>`) o `texto_titulo_o_descripcion` (coincidencia por palabra entera, solo si hay un único municipio). |
| `ubicacion_analisis` | texto | Ubicación usada en medianas por zona: municipio verificado → `ubicacion_raw` → vacío. **940 filas con municipio homologado y 1.434 con ubicación de cualquier tipo.** |
| `origen_ubicacion` | categórica | `pagina_anuncio`, `campo_publicado` o `sin_dato`. |
| `zona_normalizada` | texto | Zona o barrio declarado, sin forzar a municipio. |
| `municipio_homologado` | texto | **Solo los 15 municipios de La Habana**, vía `ubicaciones.py` (`homologar_municipio()`). Las zonas o barrios de Cubisima no se imputan como municipio: quedan en `ubicacion_analisis`. |

### 9.5 Habitaciones, baños y disponibilidad (Revolico)

`extraer_detalle_anuncios_revolico.py` busca la cantidad escrita por el anunciante en la **descripción**, el **título** y el **enlace (slug)**, con patrones conservadores: dígitos ("3 cuartos", "4 hab", "2 banos"), palabras ("un cuarto", "dos banos", hasta diez), notación habanera ("apto 2/4" = 2 dormitorios) y fracciones de baño ("medio baño" suma 0,5). Reglas: gana la primera aparición explícita; si el texto menciona dos cantidades distintas, ambas quedan en la evidencia y el conflicto se marca sin resolver; si no hay mención, no se rellena nada.

| Columna | Tipo | Contenido y uso |
|---|---|---|
| `habitaciones_reextraido`, `banos_reextraido` | numérico | Cantidades leídas de la descripción y, si faltan, del título. |
| `habitaciones_slug`, `banos_slug` | numérico | Cantidades escritas en el enlace, cuando no hay descripción. |
| `evidencia_detalle` | texto | Fragmento literal que justifica el valor. |
| `conflicto_detalle` | texto | Marcado cuando hay cantidades discrepantes (**72 anuncios**); no se resuelve. |
| `habitaciones_analisis`, `banos_analisis` | numérico | Valores que usan segmentación, clustering, medianas y gráficos: descripción/título → campo publicado → slug → vacío. Cobertura de Revolico: 528 habitaciones (69,9 %) y 285 baños (37,7 %). |
| `origen_habitaciones`, `origen_banos` | categórica | `descripcion_o_titulo`, `campo_publicado`, `slug` o vacío. |
| `fecha_ultima_disponibilidad` | fecha | Para anuncios no publicados: fecha del listado guardado donde aún aparecían. |
| `ventana_despublicacion` | texto | Intervalo `AAAA-MM-DD a AAAA-MM-DD` de la desaparición (153 anuncios). Es un límite con evidencia, no una fecha exacta. |
| `justificacion_disponibilidad` | texto | Explicación de por qué el anuncio sigue en el dataset pese a no ser accesible. |
| `estado_anuncio` | categórica | `publicado` (602), `anuncio_inexistente_unpublished-ad` (80), `anuncio_inexistente_cant-see-deleted-ad` (73). |
| `vendido` | booleano | `isSold` del anuncio. |
| `fecha_reextraida` | fecha ISO | `updatedOnByUser`: **fecha de la última actualización**, no de creación ni de venta. No se mezcla con `fecha_publicacion` de otras fuentes. |
| `evidencia_metadatos` | texto | Archivo de metadatos y URL de origen. |
| `alcance_dudoso` | booleano | Marca los 14 anuncios de venta de inmueble con uso mixto o dudoso (fincas, hostales, casas con bar o restaurante, almacenes, local adaptado) que **se mantienen** en el análisis por decisión de la investigadora (20/10/2026). Permite medir la sensibilidad sin reintegrar el maestro. |
| `motivo_alcance_dudoso` | categórica | Motivo de la marca: `finca`, `casa_con_finca`, `uso_mixto`, `hostal`, `casa_restaurante`, `casa_con_bar`, `almacen`, `local_adaptado`. |

**Cobertura honesta:** el techo de habitaciones y banos lo fija el texto del anuncio (153 anuncios inaccesibles y descripciones que omiten la cantidad). No se imputa nada.

## 10. Alcance: exclusiones y casos dudosos

| Artefacto | Contenido |
|---|---|
| `outputs/integracion/anuncios_no_residenciales_*.csv` | Anuncios apartados por veredicto (`producto`, `permuta`, `otro`, `alquiler`): 6 de la pasada previa y 9 alquileres de la revisión de precios < 1.000. |
| `outputs/integracion/anuncios_fuera_de_alcance_*.csv` | 28 anuncios apartados por alcance (13 fuera de La Habana, 15 que no son vivienda). |
| `revision_manual/exclusiones_alcance.csv` | Auditoría de esas 28 exclusiones: URL exacta, motivo y evidencia. Se emparejan por URL, no por posición. |
| `revision_manual/precios_bajos_1000.csv` | Revisión manual de 23 anuncios con precio de análisis < 1.000 y de los alquileres detectados en el catálogo: 9 `alquiler` (salen del maestro), 9 `no_verificable` (el anuncio se conserva sin precio), 4 `despublicado` y 1 `precio_recuperado` (12.500 USD, con la cita "Precio: 12,500"). |
| `revision_manual/alcance_dudoso.csv` | 14 anuncios de uso mixto o dudoso **incluidos** en el análisis por decisión de la investigadora (20/10/2026: todo lo que sea venta de inmueble es válido). Columnas: `fuente`, `id_local`, `url`, `motivo`, `evidencia`, `titulo`, `fecha_revision`, `estado` (`incluido_en_analisis`), `fecha_decision`, `decisor`, `nota`, `caveat_analisis` (advertencia de que el precio puede incluir tierra, licencia o equipamiento). |

El maestro vigente incluye 1.532 fichas: 1.566 capturadas − 6 no residenciales − 28 fuera de alcance. Ninguna URL excluida aparece en el maestro (control automático).

## 11. Entrevistas anónimas (`procesar_entrevistas.py`)

El export del formulario (CSV o XLSX) se procesa **sin persistir jamás metadatos personales**: cualquier columna de correo, nombre o teléfono se descarta antes de escribir. Las respuestas se anonimizan como `entrevista_id` E01..E0N y cada fila conserva `fecha_respuesta` (ISO cuando se puede parsear) más una columna por pregunta (`relacion`, `municipio`, `evolucion_precios`, `factores_precio`, `influencia_tasas`, `refleja_precio`, `influencia_migracion`, `factor_dominante`, `reduccion_precio`, `canales`). Salida: `outputs/entrevistas/entrevistas_codificadas_<fecha>.csv`.

| Código | Criterio | Frecuencia (n=10) |
|---|---|---:|
| `C1_necesidad_economica` | dinero, necesidad, urgencia o miseria | 9 |
| `C2_migracion` | migra*, travesía, Nicaragua, salir del país, irse del país | 10 |
| `C3_moneda_tasa` | USD, CUP, tasa(s), moneda, divisa, dólar, euro, MLC | 8 |
| `C4_canal_venta` | Telegram, WhatsApp, Facebook o grupo | 4 |
| `C5_precio_alto` | caro, carísimo, regalo o valor | 7 |
| `C6_caracteristicas` | m2, metro, baño(s) o piscina | 2 |
| `C7_municipio` | cualquier municipio de La Habana en el texto | 10 |

`A1_cita` guarda los primeros 220 caracteres como cita ilustrativa y `resumen_entrevistas_<fecha>.md` reproduce frecuencias, relación/municipio y las respuestas literales del factor dominante y de la migración. Los códigos son heurísticas de frecuencia para organizar el discurso: **no sustituyen la lectura manual ni prueban causalidad**. La exportación original con datos identificables vive en `data/entrevistas/` y no se versiona ni se publica.

## 12. Tasas y equivalencias

- El registro local de tasas no contiene `cuc_informal_cup` ni `cuc_formal_cup`: **no hay tasa de mercado registrada para el CUC**.
- Conversión vigente: `outputs/conversiones/dataset_maestro_conversion_*.csv` (USD y EUR con tasa informal y formal) y `outputs/conversiones/dataset_maestro_conversion_cuc_nominal_*.csv` (paridad nominal 1 CUC = 1 USD, decisión explícita, no tasa de mercado). El método queda en `metodo_conversion_cuc` y la paridad aplicada en `fx_cuc_usd_nominal`. Se conservan importe y moneda originales.
- Tasas registradas: **20/10/2026** (USD informal 815, formal 710,50; EUR informal 910, formal 796,26), fuente ElToque. El acceso automático al sitio está bloqueado (HTTP 403), así que los valores se transcribieron manualmente de la página y el registro guarda `estado_acceso = registro_manual` con la nota de auditoría que detalla la captura, la variación intradía del euro (881,91 / 900 / 910) y la fila de la tabla formal usada (BPA, valor de compra). Toda cifra convertida debe citar esa fecha y esa fuente.
- Los análisis por precio, zona, habitaciones, canal, segmentación y clustering **separan por moneda** y excluyen la moneda desconocida de las comparaciones de importes.

## 13. Archivos locales y política de Git

`.gitignore` excluye `data/`, `outputs/`, el HTML guardado de Revolico y los CSV derivados locales para evitar subir datos o resultados por accidente. Se versionan: código, documentación, pruebas y las decisiones manuales auditadas de `revision_manual/`. No se deben borrar ni versionar los respaldos de `data/` como parte de una revisión de documentación.
