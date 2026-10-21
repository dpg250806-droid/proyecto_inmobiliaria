# Informe preliminar del mercado inmobiliario de La Habana

**Corte de datos:** 19/10/2026 · **Tasas:** 20/10/2026 · **Revisión del documento:** 20/10/2026
**Base integrada:** `outputs/integracion/dataset_maestro_20261020_234716.csv` — 1.516 anuncios (Revolico 748, Cubisima 585, HogarEnCuba 183), 0 identificadores duplicados y 0 URL repetidas.
**Estado:** documento de resultados consolidado. No es todavía el informe final; el cierre académico (discusión, limitaciones y referencias) queda pendiente de autorización expresa.

---

## 1. Alcance, trazabilidad y exclusiones

La base se construyó en pasos documentados, sin modificar ningún archivo original:

| Paso | Fichas | Criterio |
|---|---:|---|
| Captura inicial | 1.566 | 780 de Revolico, 598 de Cubisima, 188 de HogarEnCuba |
| Exclusión por tipo de anuncio (pasada previa) | −6 | 4 productos, 1 permuta y 1 local comercial: no son vivienda en venta |
| Exclusión por alcance geográfico y de uso | −28 | 13 fuera de La Habana y 15 que no son vivienda |
| Exclusión por alquiler publicado en el catálogo de venta | −9 | 8 de Cubisima y 1 de Revolico: la descripción dice "se renta", "renta lineal" o "precio X USD mensual" |
| Exclusión por objeto que no es vivienda en venta | −7 | 2 anuncios de producto (empresa de metal, tiras de cabillas), 4 anuncios de agencia o servicios, 1 demanda de compra y 1 restaurante con mipyme |
| **Maestro vigente** | **1.516** | 100 % con identificador y URL únicos |

- La auditoría de las 28 exclusiones de alcance está en `revision_manual/exclusiones_alcance.csv` (URL exacta, motivo y evidencia); ninguna de esas URL aparece en el maestro.
- Los **9 alquileres** y el resto de la revisión de precios raros están en `revision_manual/precios_bajos_1000.csv`; los **7 anuncios de objeto no vivienda** y los **15 precios recuperados** de la segunda pasada, en `revision_manual/precios_pendientes_recuperados.csv`. Todos llevan el fragmento de descripción que lo demuestra.
- **14 anuncios de alcance dudoso se conservan** por decisión de la investigadora (20/10/2026: *todo lo que sea venta de inmueble es válido*): 6 fincas, 2 de uso mixto, 1 local adaptado a vivienda, 1 hostal, 1 casa-restaurante, 1 casa con bar, 1 almacén y 1 casa con finca. Quedan marcados en `alcance_dudoso` y listados en `revision_manual/alcance_dudoso.csv`. La **sensibilidad es nula**: al retirarlos, ninguna mediana por fuente y moneda se mueve (0,00 %; tabla 9b en `outputs/preguntas/`).
- La unidad de análisis es **el anuncio**, no la transacción cerrada. Ningún precio se imputa: cuando un campo no existe, no se extrajo o requiere revisión manual, queda marcado con esa distinción (`precio_sospechoso`, `veredicto_revision`, `origen_precio`).

### 1.1 Auditoría de precios "raros" (umbral < 1.000)

Se revisaron uno a uno **23 anuncios** con precio de análisis inferior a 1.000 (más los alquileres detectados en el catálogo), consultando la ficha individual de cada anuncio (Cubisima y Revolico, 20/10/2026) y leyendo título, descripción y campo de precio:

| Resultado | Anuncios | Detalle |
|---|---:|---|
| **Alquileres** (salen del maestro de ventas) | 9 | 8 de Cubisima (el "precio" publicado es la renta mensual) y 1 de Revolico ("se rebaja poco a poco del pago de la renta") |
| **Precio no verificable** (el anuncio se conserva, sin precio) | 9 | Marcadores de precio ("111", "123") o descripciones sin importe; también 4 fichas de Cubisima cuyo importe publicado es compatible con un número truncado (precedente: "18.00" con descripción "18 000 usd") |
| **Precio reextraído** | 1 | `rev_000163`: la descripción dice "Precio: 12,500" (coma de millares); el campo publicado (125) era la lectura errónea de "12,5" con coma decimal. El precio real es **12.500 USD** |
| **Anuncios despublicados** (sin precio) | 4 | Comprobados el 20/10/2026; sus importes ("150", "350") no son verificables |

**Consecuencia estadística:** el mínimo de precio utilizable pasó de 100 CUC a 1.000 CUC y de 111 USD a 1.200 USD. Los precios más bajos del catálogo **no son precios de venta**: son rentas mensuales publicadas en la sección de venta, marcadores de "precio a concertar" o errores de lectura de separadores de millares. Este hallazgo se contrasta con la documentación externa en `fuentes_externas.md` (§3).

## 2. Fuentes y cobertura de datos

| Fuente | Anuncios | Precio (publicado) | Precio (análisis) | Ubicación | Municipio homologado | Habitaciones | Baños | Fecha |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cubisima | 585 | 91,3 % | 530 (90,6 %) | 100 % | 98 (16,8 %) | 100 % | 100 % | 100 % |
| HogarEnCuba | 183 | 100 % | 183 (100 %) | 100 % | 183 (100 %) | 100 % | 100 % | 88,5 % |
| Revolico | 748 | 94,7 % | 691 (92,4 %) | 86,9 % | 650 (86,9 %) | 70,3 % | 38,0 % | 79,5 % |

- **Revolico** es el único volumen grande y a la vez el de peor metadato: el campo publicado cubre municipio en 38,1 %, habitaciones en 9,2 %, banos en 0 % y fecha en 0 %. La página individual de cada anuncio sí responde y de ahí se recuperaron municipio (650), fecha (`updatedOnByUser`, 595) y texto completo, base de la reextracción de habitaciones (526) y banos (284). El listado en línea sigue bloqueado por Cloudflare: se trabaja con el HTML guardado y con la ficha individual.
- **Cubisima** es la fuente estructurada más completa (habitaciones, baños, zona y fecha en el 100 %), y la única con precio masivo en CUC. Su campo `ubicacion` mezcla municipios con zonas y barrios: solo 99 fichas coinciden con uno de los 15 municipios de La Habana, y se conservan como `ubicacion_analisis` sin imputar.
- **HogarEnCuba** publica el 100 % de los campos estructurados y es la **única** que declara superficie, pero en 9 de 183 fichas (4,9 %); sus fechas son relativas ("hace 2 años"), por lo que 162 de 183 tienen fecha convertida y no exacta.
- Fechas de Cubisima en formato `dd/mm/yyyy` (rango 17/10/2023 a 12/10/2026, ninguna posterior al corte; se parsean con `dayfirst`, nunca como texto).
- La superficie (m²) queda **fuera del análisis**: Revolico y Cubisima no la publican de forma sistemática y HogarEnCuba solo en el 4,9 % de las fichas. Se conserva como traza en el maestro.

## 3. Política de precios y monedas

- 1.404 de 1.516 anuncios (92,6 %) tienen precio de análisis; los 112 restantes se reportan como sin precio, con su motivo.
- `origen_precio`: 1.363 desde el campo publicado, 41 por reextracción manual documentada (con cita en `evidencia_precio`) y 112 excluidos por ausencia o sospecha.
- `precio_sospechoso` marca 151 anuncios: **89 porque el campo publicado no declara moneda** y **62 con un problema real de precio o moneda** (CUC y CUP incluidos). De los 151, 41 siguen siendo utilizables porque la revisión manual recuperó el importe del texto.
- **CUP**: los 3 anuncios con precio en CUP quedan marcados y fuera de toda conversión y de toda estadística de precio.
- **EUR (n=4)**: se conservan en euros porque la descripción del vendedor lo dice literalmente, aunque en HogarEnCuba el título y el JSON-LD digan USD. `HEC1925` (620.000) y `HEC2258` (50.000) son de HogarEnCuba, `cubisima_000018` (48.000) es de Cubisima y `rev_000372` (125.000, apartamento frente al Malecón) es de Revolico, con el importe recuperado del texto. El conflicto se documenta como limitación y **no se interpretan**.
- **CUC**: 515 anuncios con precio; se valoran con paridad nominal declarada 1 CUC = 1 USD porque no hay tasa de mercado registrada para el CUC. Es una convención de cálculo, no una tasa, y no se presenta como conversión verificada.
- Conversiones USD/EUR: tasa informal y formal del registro del **20/10/2026** (USD 815 / 710,50; EUR 910 / 796,26), leída de ElToque. El acceso automático al sitio está bloqueado (HTTP 403), por lo que los valores se transcribieron manualmente y quedan en un registro auditable con fecha, fuente y nota, incluida la variación intradía del euro (881,91 / 900 / 910, de donde se toma la cifra de las 17:00).

## 4. Resultados por pregunta de investigación

### 4.1 Precio central por fuente y moneda (pregunta secundaria 1)

| Fuente | Moneda | n | Mediana | Media | Mínimo | Máximo |
|---|---|---:|---:|---:|---:|---:|
| Cubisima | CUC | 515 | 25.000 | 53.437 | 1.000 | 800.000 |
| Cubisima | USD | 14 | 22.500 | 69.179 | 5.000 | 600.000 |
| Cubisima | EUR | 1 | 48.000 | 48.000 | 48.000 | 48.000 |
| HogarEnCuba | USD | 181 | 60.000 | 127.254 | 5.500 | 1.300.000 |
| HogarEnCuba | EUR | 2 | 335.000 | 335.000 | 50.000 | 620.000 |
| Revolico | USD | 690 | 25.000 | 50.305 | 1.200 | 900.000 |
| Revolico | EUR | 1 | 125.000 | 125.000 | 125.000 | 125.000 |

La mediana es el centro robusto: las medias quedan muy por encima por la cola de anuncios caros (hasta 1,3 millones en HogarEnCuba). Solo USD es comparable entre fuentes; las filas con n<30 (EUR: n=1, n=2 y n=1) se muestran por trazabilidad y no se interpretan. **Las medianas no cambiaron respecto de la versión anterior a la auditoría de precios** (25.000 / 25.000 / 60.000): la limpieza de artefactos afectan a la cola, no al centro.

### 4.2 Variación entre municipios (pregunta secundaria 2)

Municipios homologados (solo los 15 de La Habana; n≥5 por fuente y moneda; USD):

| Municipio | Revolico (n; mediana) | HogarEnCuba (n; mediana) |
|---|---|---|
| Playa | 132; 50.000 | 48; 142.500 |
| Plaza de la Revolución | 87; 45.000 | 38; 77.500 |
| Diez de Octubre | 98; 33.500 | 15; 55.000 |
| Habana del Este | 35; 25.000 | 11; 75.000 |
| Habana Vieja | 31; 28.000 | 6; 46.500 |
| Boyeros | 23; 23.500 | 6; 85.000 |
| Arroyo Naranjo | 34; 15.000 | 5; 20.000 |
| Centro Habana | 80; 15.000 | 19; 35.000 |
| Cerro | 31; 15.000 | 13; 21.000 |
| Marianao | 14; 13.250 | 7; 50.000 |
| La Lisa | 19; 13.000 | 6; 37.500 |
| San Miguel del Padrón | 6; 9.000 | — |
| Guanabacoa | 12; 8.500 | 3 (n<5) |
| Cotorro | 2; 5.000 | 1 (n<5) |
| Regla | — | 3 (n<5) |

El orden de municipios es estable en Revolico (Playa y Plaza arriba; Cotorro, Guanabacoa y San Miguel del Padrón abajo) y HogarEnCuba repite los mismos barrios altos con importes mayores, pero la diferencia entre fuentes (Playa 50.000 frente a 142.500) es **descriptiva, no causal**: refleja composición y selección de anuncios, no un precio único de mercado. Las zonas de Cubisima (Miramar, Plaza, Nuevo Vedado, Playa Santa Fe, Vedado, Habana Vieja…) se reportan aparte, sin mezclarlas con municipios.

### 4.3 Habitaciones y precio (pregunta secundaria 3)

Correlación de Spearman descriptiva, por fuente y moneda:

| Fuente | Moneda | Habitaciones (rho; n) | Baños (rho; n) |
|---|---|---|---|
| HogarEnCuba | USD | 0,610; 181 | 0,731; 181 |
| Cubisima | CUC | 0,609; 515 | 0,698; 515 |
| Revolico | USD | 0,592; 495 | 0,561; 269 |
| Cubisima | USD | 0,627; 14 (exploratorio) | 0,852; 14 (exploratorio) |

Medianas observadas (solo grupos con n≥5; el detalle con n<5 queda en `outputs/preguntas/preguntas_resueltas_*.md`):

| Habitaciones | Revolico USD (n; mediana) | Cubisima CUC (n; mediana) | HogarEnCuba USD (n; mediana) |
|---|---|---|---|
| 1 | 50; 10.500 | 49; 10.000 | 9; 18.000 |
| 2 | 201; 20.000 | 169; 15.000 | 41; 30.000 |
| 3 | 163; 40.000 | 140; 35.000 | 41; 55.000 |
| 4 | 53; 70.000 | 82; 60.000 | 44; 87.500 |
| 5 | 11; 75.000 | 26; 92.500 | 15; 160.000 |
| 6 | 6; 132.500 | 6; 145.000 | 16; 90.000 |
| 7 | 5; 75.000 | 6; 147.500 | 4 (n<5) |
| 8+ | 4; 550.000 (n=4, no se interpreta) | 4; 250.000 (n=4, no se interpreta) | 5; 180.000 |

La asociación es positiva y consistente en las tres fuentes y en las dos variables: a más habitaciones y más baños, mayor precio. La correlación no implica causalidad y está parcialmente condicionada por la cobertura: en Revolico los baños se conocen en el 37,7 % de los anuncios y el subconjunto analizable sesga hacia fichas mejor descritas.

### 4.4 Características de las viviendas caras (pregunta secundaria 4)

Solo Cubisima publica características auxiliares; se compara el tercio superior de precio con el resto **dentro de CUC** (n=186 con precio ≥ 45.000 frente a n=329):

| Característica | % en el tercio superior | % en el resto | Diferencia (pp) |
|---|---:|---:|---:|
| Garaje | 65,6 | 17,9 | +47,7 |
| Jardín | 46,8 | 9,4 | +37,4 |
| Terraza | 54,8 | 26,1 | +28,7 |
| Patio | 68,3 | 53,2 | +15,1 |
| Piscina | 13,4 | 2,7 | +10,7 |
| Balcón | 31,7 | 31,9 | −0,2 |

Un 0 significa que la característica no fue declarada en la ficha, no que no exista. En USD no se calcula el tercio superior porque solo hay 14 anuncios de Cubisima con precio en USD; por debajo de 30 observaciones los dos grupos no son interpretables.

### 4.5 Canales informales y fuentes estructuradas (pregunta secundaria 5)

| Canal | Moneda | Anuncios | Mediana | Con habitaciones | Con baños | Fecha de análisis |
|---|---|---:|---:|---:|---:|---:|
| Informal — Revolico | USD | 690 | 25.000 | 495 (71,7 %) | 269 (39,0 %) | 79,5 % |
| Estructurado — Cubisima | CUC | 515 | 25.000 | 515 (100 %) | 515 (100 %) | 100 % |
| Estructurado — HogarEnCuba | USD | 181 | 60.000 | 181 (100 %) | 181 (100 %) | 88,4 % |

Diferencias observables entre canales:

1. **Volumen y cobertura**: Revolico aporta 748 fichas con metadato pobre; las plataformas estructuradas aportan menos anuncios con metadato casi completo. Consultar la página de cada anuncio es lo que convierte un clasificado informal en una fuente utilizable.
2. **Precio**: las medianas USD de Revolico (25.000) y HogarEnCuba (60.000) difieren; la diferencia es de composición (HogarEnCuba publica viviendas más grandes y más caras) y no un "precio del canal".
3. **Moneda**: Revolico concentra la oferta en USD; Cubisima ofrece CUC masivo; HogarEnCuba casi solo USD. Solo USD es comparable entre canales.
4. **Transparencia de la oferta**: las zonas de Cubisima son más específicas (barrios turísticos), mientras que Revolico exige reconstruir el municipio desde el texto.
5. **Contaminación del catálogo**: solo en el canal informal de plataformas (Cubisima) aparecen alquileres publicados en la sección de venta; el proyecto los detecta y los retira (sección 1.1).

### 4.6 Conversión de moneda y tasas (pregunta secundaria 7)

- Tasas registradas: **20/10/2026** (USD informal 815, formal 710,50; EUR informal 910, formal 796,26), fuente ElToque; acceso automático bloqueado y valores transcritos manualmente (registro en `data/tasas/`).
- El mismo precio cambia de valor equivalente según la tasa: la divergencia entre informal y formal es del **14,7 % en USD** y del **14,3 % en EUR**. Es una aritmética de conversión, no una medida de mercado.
- CUC: 515 anuncios con paridad nominal 1 CUC = 1 USD, mediana equivalente 25.000 USD. No es tasa de mercado y no se usa como precio en dólares.
- EUR: 2 fichas de HogarEnCuba (mediana convertida 374.049 USD), 1 de Cubisima (53.595 USD) y 1 de Revolico (139.571 USD): ilustrativas, no estimaciones poblacionales.

### 4.7 Agrupamiento de las viviendas (pregunta secundaria 6)

k-means (k=3) por moneda, sobre precio, habitaciones y banos, con casos completos (≥30 observaciones por moneda; EUR queda fuera con n=3). Los grupos se ordenan por mediana de precio:

| Moneda | Grupo | Anuncios | Mediana de precio | Mediana habitaciones | Mediana baños |
|---|---|---:|---:|---:|---:|
| CUC | Económico | 271 | 12.000 | 2 | 1 |
| CUC | Medio | 190 | 55.000 | 3 | 2 |
| CUC | Alto | 54 | 120.000 | 5 | 4 |
| USD | Económico | 221 | 25.000 | 2 | 1 |
| USD | Medio | 193 | 90.000 | 4 | 3 |
| USD | Alto | 33 | 430.000 | 7 | 6 |

El patrón es nítido y consistente entre monedas: el grupo alto concentra más habitaciones y más baños, y el económico las viviendas más pequeñas. El cluster USD "alto" es pequeño (33 anuncios) y concentra los precios extremos (hasta 1,3 millones): se describe, no se generaliza.

**Estabilidad y decisión metodológica.** Con el precio en escala lineal la solución de k-means dependía de la semilla (en CUC el grupo "alto" variaba entre 30 y 37 anuncios y la mediana del grupo "medio" entre 55.000 y 64.500). Por eso el agrupamiento usa **log(precio)**, que es la forma natural de una distribución de precios multiplicativa, y k-means con **10 reinicios** conservando la solución de menor inercia. Con esa definición la solución es estable: en 5 semillas el tamaño de cada grupo varía en un máximo de 5 anuncios y su mediana en un máximo de 1.000 (`outputs/clustering/estabilidad_clusters_*.csv`).

La segmentación por terciles de precio (33/66) confirma el mismo gradiente dentro de cada moneda: en CUC el tercio alto son 171 anuncios (38 con 5+ habitaciones, mediana 150.000; 109 con 3-4, 72.000; 24 con ≤2, 60.000) y en USD 214 anuncios (57 con 5+, 200.000; 128 con 3-4, 105.000; 29 con ≤2, 80.000). Los perfiles con n<5 no se interpretan.

### 4.8 Migración, oferta y demanda (pregunta secundaria 8)

Con los datos disponibles **no es posible medir** el efecto de la migración: la muestra de anuncios es transversal y las fechas útiles de Revolico son casi todas de agosto a octubre de 2026 (1 anuncio de mayo de 2025, 2 de agosto, 111 de septiembre y 487 de octubre de 2026 sobre 601 fechas de página). No hay serie temporal de precios ni de oferta, y por tanto no existe panel 2020-2026 que permita separar migración, crisis económica, desmonetización y tasa de cambio.

Lo que sí puede afirmarse es que la evidencia transversal es **compatible** con la hipótesis de una oferta presionada: el grupo económico concentra 215 de los 437 casos completos en USD (mediana 25.000) y 271 de 515 en CUC (mediana 12.000), y en HogarEnCuba la media (127.254) está muy por encima de la mediana (60.000) por el peso de los anuncios caros. La verificación de esa hipótesis requiere la serie temporal que este proyecto no tiene.

### 4.9 Qué explica el precio y qué queda sin cobertura (pregunta secundaria 9)

- 1.404 de 1.516 anuncios (92,6 %) con precio; 1.342 con fecha de análisis; 1.418 con ubicación y 931 con municipio homologado; 1.294 con habitaciones, 1.052 con baños y 1.311 con al menos una de las dos variables de tamaño.
- El techo de las variables de tamaño lo fija el texto del anuncio: en Revolico, 153 anuncios son inaccesibles y no tienen descripción, y otros anuncios publicados no mencionan la cantidad; el campo publicado solo trae habitaciones en 69 fichas y nunca trae banos, mientras el texto, el título o el enlace permiten obtener 527 habitaciones y 284 banos.
- La cobertura de la superficie no llega al 100 % en ninguna fuente, por lo que **no se usa como variable explicativa**.
- Las 14 fichas de alcance dudoso y los 112 anuncios sin precio verificable son el faltante principal: ninguna se resuelve por imputación.

## 5. Triangulación con fuentes externas

El contraste con el registro publicado sobre el mercado habitacional habanero está documentado en [`fuentes_externas.md`](fuentes_externas.md) (7 fuentes consultadas el 20/10/2026: una agencia de prensa —AFP/France24—, un medio digital y cuatro análisis de una agencia inmobiliaria con interés comercial). En síntesis:

- **Dirección coincidente.** AFP (24/04/2026) describe una reanimación del mercado en 2026 con precios al alza en Miramar, Nuevo Vedado y Vedado, y valores **40-50 % por debajo** del máximo del deshielo diplomático; los análisis comerciales (junio y octubre de 2025, septiembre de 2026) estiman caídas reales del **40-60 %** en cinco años y citan el éxodo de más de 1,5 millones de emigrados desde 2020 como causa de la sobreoferta. Las entrevistas del proyecto coinciden en el mecanismo (8 de 10 nombran la migración como factor dominante).
- **Magnitud no verificable aquí.** El proyecto no puede medir esa caída: su muestra es transversal. Lo que sí muestra es que nuestros precios pedidos de octubre de 2026 son del mismo orden de magnitud que los "precios actuales" de esas fuentes, y que en los municipios periféricos nuestras medianas coinciden con sus promedios orientativos (San Miguel del Padrón 9.000 frente a 8.000; Guanabacoa 8.500 frente a 9.000; Centro Habana 15.000 dentro de su banda 12.000-40.000).
- **Divergencia que el proyecto resuelve.** Una de esas fuentes afirma que "en zonas vulnerables se llegaron a vender casas por 100, 200, 600 dólares". La auditoría de precios <1.000 muestra que, en el catálogo de 2026, los anuncios en ese rango son **alquileres publicados en la sección de venta**, marcadores de precio o errores de lectura de separadores de millares. Es una advertencia metodológica: esas cifras no son contrastables y el proyecto las depura en lugar de reproducirlas.
- **Límite de fuente.** El organismo oficial de estadística (ONEI) no fue accesible desde el entorno de trabajo y no se consultó ningún índice oficial de precios de vivienda: no existe una serie pública que contrastar.

## 6. Triangulación con entrevistas anónimas

Base: 10 entrevistas (E01–E10; 15/10/2026 a 19/10/2026) procesadas con `procesar_entrevistas.py`, que anonimiza, no persiste metadatos personales y codifica temas con palabras clave acento-insensibles. Salidas auditables: `outputs/entrevistas/entrevistas_codificadas_*.csv` (códigos C1–C7) y `resumen_entrevistas_*.md` (respuestas literales). Perfil: 4 propietarios, 2 inquilinos, 2 herederos, 1 asesor inmobiliario y 1 familiar de propietarios; viviendas de referencia en 10 de Octubre (5), Plaza de la Revolución (2), Centro Habana (2) y Playa (1). Es una muestra pequeña, no probabilística y autoseleccionada: describe percepciones y mecanismos, no prevalencias ni causalidad.

- **Migración**: las 10 respuestas la mencionan (C2 = 10/10) y 8 de 10 la nombran dentro del factor dominante (E02–E04 y E06–E09 la eligen como factor único o principal; E05 la combina priorizando la crisis económica; E01 señala solo la crisis; E10 señala los tres factores sin elegir uno). Mecanismo repetido: la emigración aumentó la oferta de casas para financiar la salida, la demanda local sin dinero cayó y la urgencia empujó los precios a la baja (E07: ventas "con todo dentro hasta por 4 mil dólares"; E09: caídas percibidas "hasta un 50 %"; E10: vender "para poder tener liquidez y solvencia para salir del país"). Son percepciones: el proyecto no tiene serie temporal y no puede medir ni refutar esa caída.
- **Evolución percibida desde 2020**: 7 de 10 describen descenso (E02–E04, E06–E09), 1 no distingue (E01), 1 percibe un periodo variable con posible revalorización (E05) y 1 un "aumento sin límites" por inflación (E10). Se reporta como disenso, sin promediar percepciones.
- **Urgencia y necesidad** (pregunta 9): 8 de 10 mencionan urgencia, necesidad de dinero o emigración como motivo de la reducción (E01–E04, E06, E07, E09, E10); 2 el estado o la ubicación (E05, E08). Coincide con C1 (necesidad o urgencia) presente en 9 de 10. La motivación no se observa en los anuncios y no se estima.
- **Ubicación**: 6 de 10 la nombran factor principal (E01, E02, E05, E06, E09, E10), 2 el estado constructivo (E03, E07) y 2 el tamaño (E04, E08). En los anuncios la dirección es la misma y medible (Revolico USD: Playa 50.000 con n=130 frente a Plaza 45.000 con n=87 y municipios bajos con n≥5), como asociación descriptiva, sin estimar cuánto aporta la ubicación.
- **Moneda y tasas**: 8 de 10 mencionan moneda o tasas (C3) y describen precios anclados en divisas con tasas que afectan sobre todo a la conversión a moneda nacional (E04: "la vivienda tiene un precio en usd y las tasas solo influyen para el cambio a mn"; E10: "todo se rige por la tasa de cambio"). En los datos, los precios utilizables están casi todos en divisas (885 USD, 515 CUC nominal, 4 EUR) y los 3 en CUP quedaron marcados como sospechosos: la percepción tiene contraparte en el registro.
- **Canales**: 4 de 10 prefieren grupos de Telegram/WhatsApp/Facebook (E01, E02, E08, E09), 4 intermediarios (E03, E04, E05, E10) y 2 plataformas tipo Revolico (E06, E07). La comparación de fuentes apunta en la misma dirección desde el otro lado: las plataformas estructuradas documentan mejor banos y zona que el clasificado informal.
- Frecuencias de código: C1 necesidad económica 9/10, C2 migración 10/10, C3 moneda y tasa 8/10, C4 canal de venta 4/10, C5 precio alto 7/10, C6 características 2/10, C7 municipio 10/10.
- El triángulo se queda en evidencia cualitativa: nunca se usa para estimar efectos ni para afirmar que la migración causó un porcentaje de cambio en los precios.

## 7. Limitaciones

1. **Anuncios ≠ transacciones**: se observan precios pedidos, no precios pactados; no hay fecha de operación ni superficies verificadas.
2. **Sin serie temporal**: 600 de 601 fechas útiles de Revolico son de agosto a octubre de 2026; no hay panel 2020-2026 y no se puede medir evolución de precios ni el efecto de la migración.
3. **Sesgo de disponibilidad en Revolico**: 153 de 754 anuncios ya no son accesibles (80 despublicados, 73 eliminados). No se descartan: quedan marcados con `fecha_ultima_disponibilidad`, `ventana_despublicacion` y `justificacion_disponibilidad`; la desaparición solo puede acotarse al intervalo 29/09–18/10/2026.
4. **Cobertura parcial de habitaciones y banos**: el techo lo fija el texto del anuncio (153 inaccesibles y descripciones que omiten la cantidad). La cadena de decisión es descripción → título → campo publicado → enlace; 72 anuncios con cantidades discrepantes quedan marcados en `conflicto_detalle` sin resolverse. No se imputa nada.
5. **Contaminación del catálogo de venta**: nueve anuncios eran alquileres y uno más era una permuta; se retiraron del maestro, pero no se puede descartar que queden casos similares con precios por encima de 1.000. La revisión de alquileres se hizo sobre las 594 fichas de Cubisima y las 754 de Revolico con el texto completo, por lo que la cobertura de esta limpieza es alta, pero no total.
6. **Precios sin verificar**: 112 anuncios (59 sin precio en texto, 22 no verificables, 11 que solo repiten el precio ya marcado, 8 no disponibles, 8 despublicados, 3 en CUP y 1 con valor improbable) quedan listados con motivo y acción sugerida; no se imputa ninguno. La revisión del 20/10/2026 recuperó 15 de los 134 anteriores y retiró 7 anuncios que no eran oferta de venta de vivienda; el resto son anuncios cuyo vendedor nunca publicó un precio.
7. **Municipios y zonas no son equivalentes**: solo 931 fichas tienen municipio homologado (Revolico 650, HogarEnCuba 183, Cubisima 98, y en Cubisima el nombre de la zona coincide con un municipio, no con una municipalización). Las zonas de Cubisima se analizan aparte.
8. **Superficie (m²) excluida**: 0 % en Revolico y Cubisima, 9/183 (4,9 %) en HogarEnCuba.
9. **Precios en CUP (3) y EUR (4) no interpretables**: los CUP quedan como sospechosos y los EUR se conservan por literalidad de la descripción, en conflicto con el JSON-LD de HogarEnCuba.
10. **CUC convertido por paridad nominal**: no existe tasa de mercado registrada; la conversión 1:1 es una convención declarada y el bloque en CUC puede estar inflado respecto del mercado en USD.
11. **Tasas de referencia, no operadas**: registro del 20/10/2026 leído a mano de ElToque por bloqueo (HTTP 403), con variación intradía del euro. Toda cifra convertida cita esa fecha y esa fuente.
12. **Agrupamiento descriptivo**: k-means con k=3 y log(precio) es estable en 5 semillas, pero sigue siendo una partición de los datos disponibles, no una tipología de la vivienda; el grupo "alto" en USD tiene 32 anuncios.
13. **Fuentes externas con intereses**: cuatro de las siete fuentes contrastadas son blogs de una agencia inmobiliaria con interés comercial; se citan como comentario de mercado y no como medición.
14. **Sin scraping de Revolico ni de redes sociales**: se usa HTML guardado; Facebook y Telegram solo han aportado evidencia manual y la encuesta anónima.
15. **Muestra de entrevistas no probabilística**: describe mecanismos y percepciones; no estima prevalencias ni efectos.

## 8. Entregables del proyecto

| Carpeta | Contenido |
|---|---|
| `outputs/integracion/` | Maestro integrado (1.516 filas) y registro de integración |
| `outputs/limpieza_integrada/` | Maestro depurado con columnas de análisis (no sobrescribe los campos publicados) |
| `outputs/conversiones/` | Precios convertidos con tasa, fecha y método (informal, formal y nominal CUC) |
| `outputs/comparativos/` | Cobertura por fuente, comparativo por canal y sus gráficos |
| `outputs/segmentacion/` | Segmentación por terciles (33/66) y perfiles por tamaño |
| `outputs/clustering/` | k-means por moneda, centroides, prueba de estabilidad y dispersión de grupos |
| `outputs/visualizaciones/` | 8 gráficos de síntesis y resumen tabular |
| `outputs/entrevistas/` | Entrevistas codificadas (E01–E10) y resumen con citas literales |
| `outputs/validacion/` | Revisión de precios, lista de pendientes y evidencias de revisión |
| `outputs/preguntas/` | Respuestas a las 9 preguntas con tablas, sensibilidad y notas de interpretación |
| `revision_manual/` | Decisiones manuales auditadas: precios bajos, precios ausentes, precios <1.000, precios recuperados, exclusiones de alcance, alcance dudoso |

Documentación: `README.md` (estado y catálogo de scripts), `data_dictionary.md` (columnas y políticas), `fuentes_datos.md` (estado de las fuentes), `fuentes_externas.md` (triangulación con la documentación publicada), `matriz_variables_fuentes.md`, `preguntas_investigacion.md`, `cuestionario_entrevistas.md`, `diseno_encuesta_online.md`.

Reproducibilidad: `python cifras_control.py` imprime todas las cifras de control de este documento contra el maestro vigente; `python auditoria_revolico.py` verifica la consistencia de la extracción de Revolico; `python control_calidad.py` revisa compilación, documentación y estado de Git; `python -m unittest discover -s tests -t .` ejecuta la batería de pruebas.

## 9. Pendientes

1. ~~Tasas verificadas~~ — **resuelto el 20/10/2026**: registro actualizado (USD 815 / 710,50; EUR 910 / 796,26) y conversiones, gráfico de tasas y respuestas regeneradas.
2. **Revisión de los 112 precios pendientes** (lista con motivo y acción sugerida en `outputs/validacion/precios_pendientes_actualizado_*.csv`): decidir caso por caso sin imputar. En su mayoría el vendedor nunca publicó un precio, así que el trabajo pendiente es de delimitación del análisis, no de recuperación de datos.
3. **Informe final**: redacción académica con discusión, limitaciones y referencias, pendiente de autorización expresa del usuario.
