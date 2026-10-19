# Analisis del mercado inmobiliario cubano a partir de anuncios de Revolico

Proyecto academico de Introduccion a la Ciencia de Datos. Fuente principal: anuncios de viviendas en Revolico para La Habana.

## Estado de la primera auditoria

Esta es la primera etapa de diagnostico. Se conservan intactos los CSV existentes y se creo una copia de seguridad en `data/raw/` con un inventario de hashes.

Resultados principales verificados:

- 8 paginas HTML manuales de Revolico fueron procesadas.
- `enlaces_anuncios_revolico.csv`: 780 filas y 4 columnas.
- `anuncios_revolico_procesados.csv`: 780 filas y 9 columnas.
- `viviendas_revolico_candidatas.csv`: 763 filas y 9 columnas.
- `anuncios_revolico_revisar.csv`: 10 filas.
- `anuncios_revolico_excluidos.csv`: 7 filas.
- 12 titulos duplicados exactamente; 13 despues de normalizacion; 0 URLs duplicadas.
- 650 de 780 titulos contienen palabras tipo propiedad, segun la auditoria.
- Precio no disponible: 46 de 780.
- Moneda no disponible: 46 de 780.
- Municipio no disponible: 491 de 780 (~62.9%).
- Habitaciones no disponible: 710 de 780 (~91.0%).
- `texto_tarjeta` esta contaminado por contenedores compartidos y no debe usarse como feature final sin reextraer de forma individual.

## Scripts principales

- `scraper_revolico.py`: comprobacion basica de conexion a Revolico. No guarda datos.
- `leer_paginas_revolico.py`: lee las 8 paginas HTML guardadas y construye `enlaces_anuncios_revolico.csv`.
- `procesar_anuncios_revolico.py`: limpia URLs, extrae precio, moneda, municipio y habitaciones desde el titulo, clasifica los anuncios y genera los CSV segmentados.
- `auditoria_revolico.py`: auditoria exclusivamente de lectura. Genera un informe en `outputs/auditoria/`.
- `limpiar_revolico.py`: limpieza no destructiva. Genera un dataset derivado y un resumen en `outputs/limpieza/`.
- `scraper_cubisima.py`: entrada compatible que delega en `scraper_cubisima_online.py`; ya no tiene scraping al importar ni sobrescribe el CSV original.
- `scraper_cubisima_online.py` y `scraper_hogarencuba.py`: scrapers complementarios; validan respuestas, evitan CSV vacíos y guardan snapshots nuevos sin sobrescribir.
- `scraper_revolico.py`: intenta Playwright/HTTP y usa HTML local cuando no logra acceso; los outputs y cachés son fechados y no se reemplazan.
- `reprocesar_cubisima.py`: reprocesa el CSV local con el parser de moneda actual y escribe una copia auditada, sin red ni sobrescrituras.
- `reprocesar_hogarencuba.py`: revalida online solo registros con diferencias detectables y genera un snapshot nuevo con valores previos y evidencia.
- `generar_revision_precios_bajos.py`: arma la lista de precios por debajo de 100 que no tienen criterio automatico; se niega a sobrescribir una lista ya rellenada.
- `revisar_descripciones_precios_bajos.py`: abre cada anuncio de esa lista y guarda estado, precio publicado en la pagina, municipio y descripcion literal, ademas de los montos citados dentro de la descripcion; escribe CSV y MD fechados en `outputs/validacion/`.
- `revisar_precios_ausentes.py`: para cada anuncio sin `precio_analisis`, busca precio en titulo, descripcion y pagina individual con criterios conservadores (exige moneda explicita, rechaza digitos de telefono y no elige entre importes distintos); deja el veredicto por anuncio en `revision_manual/precios_ausentes.csv` (se puede reejecutar sin perder decisiones previas) y la lista pendiente de revision manual en `outputs/validacion/precios_pendientes_<fecha>.csv/.md`.
- `extraer_metadatos_revolico.py`: consulta la pagina individual de cada anuncio de Revolico y extrae municipio, provincia, fecha `updatedOnByUser`, descripcion, estado y `isSold`; la tarjeta del listado no contiene esos datos. Salida incremental y reanudable en `outputs/metadatos_revolico/`.
- `extraer_detalle_anuncios_revolico.py`: lee las descripciones ya descargadas y extrae habitaciones y banos del texto de cada anuncio de Revolico (descripcion, titulo y enlace) con patrones conservadores; anade ademas la ventana de desaparicion de los anuncios borrados o despublicados, acotada entre la fecha del listado guardado y la de la consulta. Salida fechada en `outputs/metadatos_revolico/`.
- `integrar_fuentes.py`: prefiere la copia reprocesada de Cubisima más reciente; en su ausencia lee `viviendas_cubisima.csv`.
- `convertir_precios_tasas.py`: convierte USD, EUR, CUP y, por defecto, CUC solo con tasas guardadas; `--cuc-usd-nominal` aplica equivalencia nominal 1 CUC = 1 USD (no es una tasa de mercado) unicamente a anuncios con fecha de publicacion posterior a 2021.
- `tests/test_price_currency.py`: pruebas offline de moneda, conversión, segmentación y migración.
- Scripts exploratorios: `inspeccionar_revolico.py`, `buscar_datos_ocultos_revolico.py`, `diagnostico_json_revolico.py`, `extraer_datos_revolico.py`.

## Estado local de las fuentes y precios

Los datos locales de trabajo incluyen 780 anuncios de Revolico, 598 tarjetas del snapshot reciente de Cubisima y 188 fichas del recrawl completo de HogarEnCuba. Los snapshots bajo `outputs/` son locales y no se actualizan automáticamente cuando cambia un parser.

El `viviendas_cubisima.csv` local es anterior a la corrección del parser: 571 importes visibles como euros coinciden con los importes CUC de sus URL; 54 anuncios indican “Sin precio”. Para crear una copia corregida y reconstruir el maestro:

```bash
python reprocesar_cubisima.py
python integrar_fuentes.py
```

La migración conserva el texto fuente y los valores anteriores en columnas de auditoría. No modifica el CSV original. El snapshot corregido generado es `outputs/cubisima/viviendas_cubisima_reprocesada_20261017_221516.csv`; la integración creó `outputs/integracion/dataset_maestro_20261017_221530.csv` y la conversión `outputs/conversiones/dataset_maestro_conversion_20261017_221543.csv`. Los snapshots maestros anteriores permanecen intactos.

Los snapshots históricos de HogarEnCuba se conservan sin cambios. La comparación ampliada encontró 14 registros con precio/moneda desactualizados. Se consultaron sus 14 fichas actuales (HTTP 200): el parser ahora lee el precio del JSON-LD cuyo `sku`/`identifier` coincide con el ID del anuncio, en vez de tomar importes de anuncios recomendados. La etiqueta explícita `PRECIO EN EUR` dentro de una ficha prevalece sobre una moneda contradictoria en su JSON-LD. La prueba en vivo dio 14/14 coincidencias con los datos esperados.

El snapshot `outputs/hogarencuba/viviendas_hogarencuba_revalidada_20261017_232654.csv` conserva las 155 filas del histórico y corrige 14 discrepancias; las otras 141 se mantienen identificadas como no reconsultadas en esa revalidación. Después se completó el recrawl del sitio: `outputs/hogarencuba/viviendas_hogarencuba_20261017_234325.csv` reúne 188 URLs únicas en 10 de 10 páginas, con 0 fichas fallidas. Las 14 fichas discrepantes anteriores aparecen en la captura nueva con extracción JSON-LD ligada al ID, salvo HEC2258, cuya etiqueta explícita `PRECIO EN EUR` se conserva como señal de moneda. No se reemplazaron snapshots anteriores.

`python reprocesar_hogarencuba.py` vuelve a consultar solo filas que discrepan de la evidencia local y crea una salida exclusiva. Para una captura integral actualizada puede ejecutarse `python scraper_hogarencuba.py`; el scraper guarda un snapshot nuevo y fecha sus páginas y fallos.

Se reconstruyeron los resultados desde la captura completa: maestro `outputs/integracion/dataset_maestro_20261017_234629.csv` (1.566 anuncios: 780 Revolico, 598 Cubisima y 188 HogarEnCuba) y conversión nominal CUC/USD `outputs/conversiones/dataset_maestro_conversion_cuc_nominal_20261017_234636.csv`. El análisis preliminar está en `outputs/preguntas/preguntas_resueltas_20261017_234644.md`; gráficos, comparación, segmentación y clustering nuevos se guardaron en carpetas `corrida_20261017_235245/`, sin sobrescribir salidas anteriores. El informe final sigue pendiente de las entrevistas.

Tras la revisión manual de precios bajos, el maestro añade columnas de revisión y de precio de análisis. Los 12 anuncios cuyo precio publicado resultó erróneo se reincorporaron con `precio_reextraido` (precio verificado en la descripción o el título), `moneda_reextraida` y `evidencia_precio`; el campo publicado se conserva sin corregir y su error sigue visible en `precio_sospechoso` y `veredicto_revision`. Los análisis usan `precio_analisis`/`moneda_analisis` (definidos por `precios_analisis()` en `precio_moneda.py`): la reextracción verificada primero, después el campo publicado si no está marcado como sospechoso y tiene moneda, y vacío en el resto, sin imputar. La cobertura del campo publicado se sigue midiendo con `precio_original` para no mezclar conceptos.

Una segunda pasada (`revisar_precios_ausentes.py`) busco precio en el titulo, la descripcion y la pagina individual de los 142 anuncios que no tenian `precio_analisis`: recupero 13 precios con su cita (5 de Cubisima y 8 de Revolico) y dejo 129 pendientes en `outputs/validacion/precios_pendientes_<fecha>.csv/.md` con el motivo de cada uno, para revision manual. De paso se verifico la duda sobre Cubisima: en los 52 anuncios que llegaron sin precio, la pagina individual consulta el 18/10/2026 dice literalmente \"Sin precio\"; en 6 de ellos el precio si aparecia escrito en la descripcion. Los veredictos quedan versionados en `revision_manual/precios_ausentes.csv` y `integrar_fuentes.py` los aplica junto con `precios_bajos.csv` (gana la primera lista si ambas hablan del anuncio). El maestro vigente es `outputs/integracion/dataset_maestro_20261018_225829.csv` (1.560 filas: 775 Revolico, 597 Cubisima y 188 HogarEnCuba), tras apartar 6 anuncios que no son vivienda en venta (4 productos, 1 permuta y 1 local comercial) a `outputs/integracion/anuncios_no_residenciales_<fecha>.csv`; ninguna fuente original se modifica.

Los análisis de precios originales separan moneda. No se comparan directamente importes USD, EUR, CUP y CUC. El registro actual de tasas no contiene CUC/CUP; la conversión normal deja los precios CUC como `tasa_cuc_no_disponible`. Los 545 anuncios CUC del maestro actual tienen fecha de publicación entre el 17/10/2023 y el 12/10/2026, es decir, todos posteriores a la desmonetización del CUC (2021). Por esa razón se ejecuta `python convertir_precios_tasas.py --cuc-usd-nominal`: aplica 1 CUC = 1 USD a precios no sospechosos publicados después de 2021, preserva CUC en `precio_original` y registra el método en `metodo_conversion_cuc` y la paridad en `fx_cuc_usd_nominal`. Los anuncios pre-2021 o sin fecha exacta no reciben la equivalencia (`cuc_pre_2021_no_convertido`, `sin_fecha_no_confirma_post_2021`). No representa una tasa de mercado o valor actual, no rellena tasas CUC/CUP y mantiene sin convertir los precios sospechosos. Las monedas no identificadas tampoco reciben equivalencia.

Las pruebas locales enfocadas se ejecutan con `python -m unittest discover -s tests -v`; no acceden a internet ni escriben en `outputs/`.

Los scrapers de Cubisima y HogarEnCuba se ejecutaron en vivo, guardando snapshots nuevos y fechados. Para reproducir una comprobación limitada o una captura completa:

```bash
python scraper_cubisima.py --max-pages 1
python scraper_hogarencuba.py --max-pages 1
python scraper_hogarencuba.py
python scraper_revolico.py --motor local --max-paginas 8
```

La ejecución Cubisima detectó 25 páginas y guardó 598 anuncios únicos en `outputs/cubisima/viviendas_cubisima_online_20261017_231411.csv`. El primer chequeo, limitado a una página, se conservó como snapshot separado. Revolico continúa bloqueado para acceso automático y el modo local requiere HTML dentro de `paginas_revolico/`; no se encontraron HTML en la copia de trabajo inspeccionada.

## Auditoria

Ejecutar:

```bash
python auditoria_revolico.py
```

El script solo lee los CSV y escribe un reporte nuevo en `outputs/auditoria/`. No modifica los CSV de entrada.

## Bitacora de desarrollo (cronologica)

Esta seccion resume el trabajo realizado y la fecha/hora de cada bloque, para servir como mapa del proceso.

- `2026-09-29` - Primer avance del proyecto inmobiliario (`ec45478`).
- `2026-09-29` - Mejora de limpieza y clasificacion de anuncios de Revolico (`bb70b4d`).
- `2026-09-29` - Extraccion de municipio y habitaciones en Revolico (`7132484`).
- `2026-09-29` - Reforzamiento del procesamiento de Revolico (`ec64e6f`).
- `2026-10-15` - Auditoria read-only, copia de seguridad e inventario SHA-256 (`f5100ad`).
- `2026-10-15` - Scraper hibrido de Revolico con respaldo local (`6364f57`).
- `2026-10-15` - Scraper online de Cubisima y EDA tabular (`c525060`).
- `2026-10-15` - Integracion de fuentes, visualizaciones y modulo de tasas (`c7dfc58`).
- `2026-10-15` - Conversiones USD y comparativos por canal (`631022e`).
- `2026-10-16` - Limpieza integrada, informe preliminar y AGENTS.md (`83370ad`, `98ba80c`).

- `2026-10-15 12:52` - Auditoria read-only del dataset Revolico. Se genero `outputs/auditoria/auditoria_revolico_20261015_125247.md` con ausencias, duplicados, precios sospechosos y limitaciones.
- `2026-10-15 12:52` - Copia de seguridad de los 9 CSV existentes en `data/raw/` con inventario SHA-256 en `data/raw/hash_inventario.csv`.
- `2026-10-15 13:05` - Primera ejecucion de limpieza no destructiva. Resultado: 672 filas en la base sugerida.
- `2026-10-15 13:08` - Correccion del patron de banos en el script de limpieza y segunda ejecucion. Se genero `outputs/limpieza/viviendas_revolico_variables_20261015_130807.csv`.
- `2026-10-15` - Integracion documental de `README.md`, `data_dictionary.md` y nuevos scripts de auditoria/limpieza.
- `2026-10-15` - Pruebas del scraper online: Revolico devuelve HTTP 403 (proteccion anti-bot/Cloudflare). Se implemento un scraper hibrido con diagnostico y respaldo local.
- `2026-10-15` - Instalacion de Playwright autorizada y prueba con Chrome del sistema. El desafio anti-bot persiste, por lo que el scraper cae automaticamente a paginas locales sin error fatal.
- `2026-10-15` - Pruebas adicionales contra Cloudflare: `curl_cffi` con suplantacion TLS, Playwright y Selenium standard tambien recibieron pagina "Un momento...". `undetected-chromedriver` no funciono por incompatibilidad de version (Chrome 154 vs ChromeDriver 155).
- `2026-10-15` - Conclusion operativa: la descarga online automatica de Revolico no es fiable hoy; se mantiene el flujo de paginas HTML guardadas + procesamiento reproducible.
- `2026-10-15` - Scraper online de Cubisima verificado y ejecutado: 25 paginas y 598 anuncios unicos guardados en `outputs/cubisima/`.
- `2026-10-15` - EDA reproducible para Revolico implementado en `eda_revolico.py`; reporte tabular guardado en `outputs/eda/`.
- `2026-10-15` - Verificadas fuentes cubanas adicionales (Casas Oasis, HogarEnCuba, Busca Tu Choza) y documentadas en `fuentes_datos.md`.
- `2026-10-15` - Subida a GitHub del commit `f5100ad` con el scraper hibrido, auditoria, limpieza no destructiva y documentacion. Los archivos derivados pesados (`data/`, `outputs/`, CSV reparado) se mantienen solo localmente.
- `2026-10-17 22:15` - Parser de precios conservador para USD/EUR/CUC; reprocesamiento no destructivo de Cubisima, nuevo maestro/conversion y reporte analitico. Los 7 desacuerdos de HogarEnCuba quedan pendientes por falta de HTML/evidencia completa.
- `2026-10-17 22:32` - Opcion explicita `--cuc-usd-nominal` para escenario nominal 1:1; se genero un snapshot nuevo sin cambiar el maestro ni los precios originales.
- `2026-10-17 22:49` - Scrapers Cubisima, HogarEnCuba y Revolico endurecidos contra respuestas bloqueadas, salidas vacias/sobrescritas y snapshots parciales silenciosos; `scraper_cubisima.py` ya no reescribe `viviendas_cubisima.csv`. Se corrigio el parseo de campos con tildes.
- `2026-10-17 23:14` - Corregida deteccion de paginacion de Cubisima con HTML que contiene `P�gina`; el scraper recorrió 25 paginas y guardo 598 anuncios unicos en `outputs/cubisima/viviendas_cubisima_online_20261017_231411.csv`, sin tocar CSV previos.
- `2026-10-17 23:21` - Revisados 14 anuncios discrepantes de HogarEnCuba contra fichas actuales. El parser usa JSON-LD por identificador exacto, no precios de anuncios similares; la etiqueta explícita `PRECIO EN EUR` prevalece ante conflicto. El scraper detecta paginación.
- `2026-10-17 23:27` - Revalidadas 14 fichas con HTTP 200 y generada la copia auditable de 155 filas `outputs/hogarencuba/viviendas_hogarencuba_revalidada_20261017_232654.csv`; las otras 141 conservan el valor previo, sin reconsulta web. El recrawl integral se detuvo por demora y no produjo archivo. Pasaron 19 pruebas offline.
- `2026-10-17 23:30` - La integración prioriza el snapshot de HogarEnCuba más reciente cuando los recuentos empatan; se generaron un maestro y una conversión nominal nuevos desde la copia revalidada.
- `2026-10-17 23:43` - El scraper HogarEnCuba recorrió las 10 páginas detectadas y guardó 188 fichas únicas; 0 fallidas. El snapshot `outputs/hogarencuba/viviendas_hogarencuba_20261017_234325.csv` preserva el historial y la evidencia individual del precio.
- `2026-10-17 23:46` - Regenerados maestro (1.566 anuncios), conversión nominal y análisis preliminar desde el snapshot completo; no se redactó el informe final por entrevistas pendientes.
- `2026-10-17 23:49` - Regenerados gráficos, comparación de fuentes, segmentación y clustering en carpetas fechadas. Se corrigió un caso de gráfico EUR con un solo anuncio y se excluyen monedas desconocidas de resúmenes de precio. Pasaron 21 pruebas offline y compilación en memoria de 39 scripts Python.
- `2026-10-17 23:52` - Corregida la cobertura de moneda desconocida en tablas comparativas y resúmenes visuales; nuevas salidas fechadas, sin reemplazar las previas.
- `2026-10-17 23:53` - Verificada la captura completa de HogarEnCuba: 188 URLs únicas, 10/10 páginas, 0 fallos; los 14 IDs discrepantes anteriores tienen precio/moneda actual con método de extracción registrado. Los CSV históricos siguen intactos.
- `2026-10-17 23:54` - Validación final: 22 pruebas offline, compilación en memoria de 39 archivos Python y `git diff --check` sin errores.
- `2026-10-18 00:24` - Rango de fechas de los 546 anuncios CUC de Cubisima: 17/10/2023 a 12/10/2026, 100% posteriores a 2021. La conversion nominal 1:1 quedo condicionada a esa fecha de publicacion y documentada como paridad, no como tasa; 540 convertidos y 6 precios sospechosos excluidos. 23 pruebas offline en verde.
- `2026-10-18 00:51` - Revision integral: pipeline offline completo (auditoria, EDA, limpieza, integracion, conversion, comparativo, segmentacion, clustering, preguntas, validacion, visualizaciones) y smokes de 1 pagina de Cubisima y HogarEnCuba mas Revolico local (8 paginas, 780 unicos). Corregidos: etiqueta `anuncios` de `limpieza_integrada.py` (size, no count), texto dinamico del bloque de clustering en `analisis_preguntas.py`, patron de `sospechoso` con escape ASCII, seleccion del snapshot de tasas util (ignora intentos bloqueados) y `.gitignore` para enlaces Revolico fechados. 24 pruebas offline en verde; `informe_preliminar.md` actualizado con los numeros vigentes.
- `2026-10-18 01:08` - Retirados `analisis_inmobiliario.py` (datos de ejemplo) y 4 utilidades locales de exploracion sin uso; referencias actualizadas en README, `data_dictionary.md` y `auditoria_revolico.py`. Clustering ampliado a todas las fuentes: CUC 540 (Cubisima) y USD 186 (HogarEnCuba), EUR excluida con 2 observaciones y Revolico por no tener banos; salidas renombradas a `clusters_viviendas_*` con test de `kmeans`. 25 pruebas offline en verde.
- `2026-10-18 14:18` - Revision manual de los 59 precios por debajo de 100: se abrieron los 37 que no tenian criterio automatico y se contrasto cada uno con su descripcion (`generar_revision_precios_bajos.py`, `revisar_descripciones_precios_bajos.py`). Resultado: 13 con precio del campo erroneo (la descripcion daba montos entre 6000 y 90000 USD), 4 productos, 1 permuta, 1 local comercial, 4 anuncios retirados y 14 sin precio en la descripcion. Los veredictos quedaron versionados en `revision_manual/precios_bajos.csv` y `integrar_fuentes.py` los aplica como `precio_sospechoso` con la columna `veredicto_revision`; el maestro pasa a 160 precios marcados de 1566 y la mediana de Revolico USD sube de 23500 a 25000. La revision detecto ademas un error de lectura de decimales con coma en Revolico ("7,5 USD" se leia 75) y municipios del sitio inconsistentes con el texto del anuncio; ambos quedan documentados como limitacion y el anuncio afectado esta excluido por veredicto. 27 pruebas offline en verde.
- `2026-10-18 15:45` - Reincorporacion documentada de los precios erroneos. Los 12 anuncios revisados con precio verificado en la descripcion o en el titulo pasan a `precio_reextraido`/`moneda_reextraida`/`evidencia_precio`, sin corregir el campo publicado; el nuevo `precio_analisis` (reextraccion primero, luego campo no sospechoso) y `moneda_analisis` son los que usan conversion, comparativo, segmentacion, clustering, visualizaciones y preguntas, centralizados en `precios_analisis()` de `precio_moneda.py`. Cobertura del precio de analisis: 1418 de 1566 anuncios (1406 de campo publicado, 12 reextracciones, 148 excluidos). 4 precios de Cubisima pasan de CUC a USD (18000, 20000, 50000, 90000) y 8 de Revolico suman a USD; la mediana de Cubisima USD queda en 35000 con n=4 y la de Revolico USD en 25000 con n=697. El clustering USD ahora integra 190 observaciones. Se corrigio ademas un encabezado con caracteres mal codificados en `analisis_preguntas.py`. Pipeline regenerado completo; 31 pruebas offline en verde.
- `2026-10-18 18:01` - Municipio y fecha de Revolico desde la pagina del anuncio. La tarjeta del listado guardado no contiene municipio ni fecha; `extraer_metadatos_revolico.py` consulto la pagina individual de los 780 anuncios (espera, reintentos, salida incremental reanudable en `outputs/metadatos_revolico/`) y extrajo del `__APOLLO_STATE__` el municipio (`municipio_reextraido`, 622 con metodo `apollo`), la provincia, la fecha `updatedOnByUser` (`fecha_reextraida`, 622 anuncios, del 17/05/2025 al 18/10/2026; es fecha de actualizacion, no de creacion), el estado y `isSold`. La consulta mostro ademas que 158 anuncios ya no estan accesibles (83 despublicados, 75 borrados), un sesgo de disponibilidad que queda documentado. `integrar_fuentes.py` anade `ubicacion_analisis` (municipio verificado primero, campo publicado despues) y `origen_ubicacion`, que ya usan la tabla por municipio de `analisis_preguntas.py` y el grafico de medianas: el municipio de Revolico pasa de 289 a 677 anuncios de cobertura de analisis y por primera vez hay medianas por municipio dentro de Revolico (Playa 50000 con n=137, Plaza 45000 con n=85). `data_dictionary.md` documenta las 8 columnas nuevas. Pipeline regenerado completo; 38 pruebas offline en verde.
- `2026-10-18 19:46` - Habitaciones y banos leidos del texto de cada anuncio, y ventana de desaparicion de los borrados. `extraer_detalle_anuncios_revolico.py` busca la cantidad escrita por el anunciante en la descripcion, el titulo y el enlace (slug) de los 780 anuncios de Revolico, con patrones conservadores (digitos, palabras hasta diez, notacion habanera "apto 2/4", fracciones de bano "medio bano" y "N banos y medio"); primera aparicion explicita gana, los conflictos titulo/descripcion quedan marcados sin resolver y no se imputa nada. Un fallo del parser (sumaba 1 a los digitos) se detecto con las pruebas nuevas y se corrigio antes de regenerar el maestro. `detalle_analisis()` de `precio_moneda.py` fija la precedencia descripcion/titulo > campo publicado > slug, y ya usan segmentacion, clustering, comparativo, visualizaciones y preguntas. Cobertura de Revolico: habitaciones 532 de 780 (antes 70) y banos 289 (antes 0); el techo lo fija el texto, porque 158 anuncios no estan accesibles y otros no mencionan la cantidad. Los 158 anuncios no publicados quedan documentados con `fecha_ultima_disponibilidad` (2026-09-29, timestamp de Cloudflare del listado guardado), `ventana_despublicacion` (2026-09-29 a 2026-10-18) y `justificacion_disponibilidad`: la pagina borrada no conserva fecha, asi que la desaparicion solo puede acotarse a ese intervalo con evidencia. El m2 queda excluido del analisis (Revolico y Cubisima 0%, HogarEnCuba ~5%: ninguna fuente lo publica al 100%); se conserva como traza y su cobertura como hallazgo comparativo. Con habitaciones y banos reales, Revolico entra por primera vez en el clustering USD (438 observaciones, antes 190 solo Cubisima y HogarEnCuba). `data_dictionary.md` documenta las 13 columnas nuevas. Pipeline regenerado completo; 46 pruebas offline en verde.
- `2026-10-18 23:19` - Precios ausentes, exclusion de no residenciales y cadena por titulo. `revisar_precios_ausentes.py` busco precio en titulo, descripcion y pagina individual de los 142 anuncios sin `precio_analisis` con criterios conservadores (exige moneda explicita, `$` solo no basta, 7+ digitos sin separador se tratan como posible telefono, dos importes distintos no se resuelven solos, CUP queda para validacion manual): recupero 13 precios con cita (5 de Cubisima, entre ellos 48000 EUR y cuatro USD, y 8 de Revolico) y dejo 129 en `outputs/validacion/precios_pendientes_<fecha>.csv/.md` con su motivo para revision manual. Se verifico la duda sobre Cubisima: en los 52 anuncios que llegaron sin precio, la pagina individual consulta el 18/10/2026 dice literalmente \"Sin precio\"; 6 de ellos si traian el precio escrito en la descripcion. Los veredictos quedan versionados en `revision_manual/precios_ausentes.csv` (una reejecucion conserva las decisiones previas) y `integrar_fuentes.py` los aplica con `precios_bajos.csv`, registrando todos los veredictos en `veredicto_revision` pero marcando `precio_sospechoso` solo con los excluyentes; la politica de consulta distingue `sin_precio_en_texto` (pagina verificada en vivo) de `consulta_fallida`, `no_consultado_sin_red` y `anuncio_no_disponible` (Revolico devuelve estado en ingles, `published`; el primer intento marco 27 falsos `consulta_fallida` y se corrigio). `excluir_no_residenciales()` aparta del maestro los veredictos `producto`, `permuta`, `otro` y `alquiler`: 6 anuncios quedan documentados en `outputs/integracion/anuncios_no_residenciales_<fecha>.csv`. Se corrigio `tipo_vivienda` de Revolico (antes la primera palabra del titulo metia precios y telefonos como tipos, 734 filas numericas; ahora clasificacion por palabras clave, 138 `no_clasificado`) y la cadena de detalle admito el titulo como respaldo cuando la descripcion no menciona la cantidad (`apto 1/4`), lo que suma 31 habitaciones. Maestro vigente `dataset_maestro_20261018_225829.csv`: 1.560 filas, precio de analisis 1431 (91,7%), 154 precios sospechosos, 25 reextracciones y 129 excluidos de precio; habitaciones 535/775 y banos 288/775 en Revolico. Pipeline regenerado completo (incluida la conversion nominal CUC desde el maestro nuevo); 58 pruebas offline en verde.

## Limitaciones conocidas

- Las paginas HTML originales estan ignoradas por Git; por tanto, el repositorio contiene derivados, pero no el material fuente descargado.
- Los selectores y patrones siguen dependiendo del HTML publicado por cada sitio; deben verificarse con capturas recientes cuando cambien las paginas.
- El campo publicado `municipio` y `habitaciones` de Revolico se extraen solo del titulo. El municipio de analisis se completa con la pagina del anuncio; las habitaciones y banos de analisis se completan con el texto del anuncio y el enlace, con cobertura parcial (535 y 288 de 775): el texto no siempre menciona la cantidad y 156 anuncios no estan accesibles.
- `texto_tarjeta` no es un texto individual confiable para analisis.
- `datos_revolico_json.csv` no es una fuente de viviendas exclusiva; contiene anuncios de productos diversos.
- Las paginas individuales de anuncios de Revolico se verificaron para municipio y fecha, pero no aportan baños, metros cuadrados, planta ni garaje en campos estructurados; esos datos solo se leen del texto libre, con las limitaciones de cobertura anteriores.
- Los CSV originales de Cubisima y los maestros anteriores pueden reflejar parsers previos; la copia reprocesada y los snapshots recientes estan separados y fechados.
- `viviendas.csv`, `viviendas_limpias.csv` y `anuncio.json` son salidas de ejemplo con datos inventados de un script retirado el 2026-10-18; se conservan como evidencia y no se usan en ningun analisis.

## Datos aun no verificados

- Correspondencia exacta entre cada anuncio y su pagina individual.
- Validez real de precios atipicos (1 USD, 52.849.429, etc.) contra el texto original.
- Cobertura completa y representatividad del muestreo de 8 paginas.
- Disponibilidad y calidad de variables adicionales (planta, garaje, balcon, terraza); los banos se leen del texto con cobertura parcial y el m2 queda excluido del analisis.
- Analisis estadistico, visualizaciones, modelos predictivos o conclusiones sustantivas del mercado.

Los CSV fuente y snapshots anteriores se mantienen intactos; los cambios de parser solo afectan nuevas ejecuciones o nuevos snapshots.

## Fuentes integradas

- Revolico: anuncios base, mas volumen y precios en USD/CUP; municipio y habitaciones con baja cobertura.
- Cubisima: 625 tarjetas locales con variables estructuradas, especialmente baños y zona; la copia reprocesada fechada refleja el parser corregido, mientras el CSV original se conserva sin cambios.
- HogarEnCuba: 188 fichas del snapshot completo actual, con superficie y baños disponibles solo en parte de los anuncios.

## Bloques disponibles

- uditoria_revolico.py: diagnostico de calidad.
- limpiar_revolico.py: base analitica derivada.
- integrar_fuentes.py: dataset maestro.
- 	asas_cambio.py: registro auditable de tasas.
- convertir_precios_tasas.py: conversion a USD.
- comparativo_fuentes.py: cobertura y mediana por fuente/canal.
- isualizaciones_fuentes.py: graficos y esquema.
- eda_revolico.py: EDA tabular.

## Limitaciones actuales

- Revolico bloqueado por anti-bot.
- Superficie (m2) disponible solo en ~5% de HogarEnCuba y en ninguna otra fuente; queda excluida del analisis.
- Moneda CUP requiere depuracion manual.
- Los anuncios no equivalen a transacciones cerradas.
- No hay tasa CUC/CUP registrada. Se conserva como predeterminado dejar CUC sin convertir; la salida nominal 1:1 solo se aplica a anuncios post-2021 con fecha exacta y queda identificada como paridad declarada, no como tasa de mercado.


## Cuestionario anonimo

Enlace: https://forms.gle/Lk3vod7cQuGHZwub9
