# Informe preliminar del mercado inmobiliario de La Habana

**Corte de datos:** 19/10/2026 · **Revisión del documento:** 20/10/2026
**Base integrada:** `outputs/integracion/dataset_maestro_20261019_223630.csv` — 1.532 anuncios (Revolico 755, Cubisima 594, HogarEnCuba 183), 0 identificadores duplicados y 0 URL repetidas.
**Estado:** documento de resultados consolidado. No es todavía el informe final; el cierre académico (discusión, limitaciones y bibliografía) queda pendiente de autorización expresa.

---

## 1. Alcance, trazabilidad y exclusiones

La base se construyó en tres pasos documentados, sin modificar ningún archivo original:

| Paso | Fichas | Criterio |
|---|---:|---|
| Captura inicial | 1.566 | 780 de Revolico, 598 de Cubisima, 188 de HogarEnCuba |
| Exclusión por tipo de anuncio (pasada previa) | −6 | 4 productos, 1 permuta y 1 local comercial: no son vivienda en venta |
| Exclusión por alcance geográfico y de uso (pasada actual) | −28 | 13 fuera de La Habana y 15 que no son vivienda |
| **Maestro vigente** | **1.532** | 100 % con identificador y URL únicos |

- La auditoría de las 28 exclusiones está en `revision_manual/exclusiones_alcance.csv`, con URL exacta, motivo y evidencia; ninguna de esas URL aparece en el maestro (control automático: 0 coincidencias).
- Las 28 fichas excluidas no se descartan: quedan disponibles para studies de alcance y para responder "qué no es vivienda en La Habana".
- **14 anuncios de alcance dudoso se conservan** en el maestro y quedan listados en `revision_manual/alcance_dudoso.csv`: 6 fincas, 2 de uso mixto, 1 local adaptado a vivienda, 1 hostal, 1 casa-restaurante, 1 casa con bar, 1 almacén y 1 casa con finca. Son anuncios cuyo objeto principal puede no ser una vivienda principal; no se excluyen sin decisión del usuario y se reportan como tales.
- La unidad de análisis es **el anuncio**, no la transacción cerrada. Ningún precio se imputa: cuando un campo no existe, no extraído o requiere revisión manual, queda marcado con esa distinción (`precio_sospechoso`, `veredicto_revision`, `origen_precio`).

## 2. Fuentes y cobertura de datos

| Fuente | Anuncios | Precio (publicado) | Precio (análisis) | Ubicación | Municipio homologado | Habitaciones | Baños | Fecha |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cubisima | 594 | 91,4 % | 536 (90,2 %) | 100 % | 100 (16,8 %) | 100 % | 100 % | 100 % |
| HogarEnCuba | 183 | 100 % | 183 (100 %) | 100 % | 183 (100 %) | 100 % | 100 % | 88,5 % |
| Revolico | 755 | 94,6 % | 691 (91,5 %) | 87,0 % | 657 (87,0 %) | 69,9 % | 37,7 % | 79,7 % |

- **Revolico** es el único volumen grande y a la vez el de peor metadato: el campo publicado cubre municipio en 38,0 %, habitaciones en 9,1 %, banos en 0 % y fecha en 0 %. La página individual de cada anuncio sí responde y de ahí se recuperaron municipio (657), fecha (`updatedOnByUser`, 602) y texto completo, que es la base de la reextracción de habitaciones (528) y banos (285). El listado en línea sigue bloqueado por Cloudflare: se trabaja con el HTML guardado y con la ficha individual.
- **Cubisima** es la fuente estructurada más completa (habitaciones, baños, zona y fecha en el 100 %), y la única con precio masivo en CUC. Su campo `ubicacion` mezcla municipios con zonas y barrios (Siboney, Miramar, Vedado): solo 100 fichas coinciden con uno de los 15 municipios de La Habana, y se conservan como `ubicacion_analisis` sin imputar municipio.
- **HogarEnCuba** publica el 100 % de los campos estructurados y es la única que declara superficie, pero en 9 de 183 fichas (4,9 %); sus fechas son relativas ("hace 2 años"), por lo que 162 de 183 tienen fecha convertida y no exacta.
- Fechas de Cubisima en formato `dd/mm/yyyy` (rango 17/10/2023 a 12/10/2026, ninguna posterior al corte; se parsean con `dayfirst`, nunca como texto).
- La superficie (m²) queda **fuera del análisis**: Revolico y Cubisima no la publican de forma sistemática y HogarEnCuba solo en el 4,9 % de las fichas. Se conserva como traza en el maestro.

## 3. Política de precios y monedas

- 1.410 de 1.532 anuncios (92,0 %) tienen precio de análisis; los 122 restantes se reportan como sin precio, con su motivo.
- `origen_precio`: 1.385 desde el campo publicado, 25 por reextracción manual documentada (con cita en `evidencia_precio`) y 122 excluidos por ausencia o sospecha.
- `precio_sospechoso` marca 147 anuncios: **92 porque el campo publicado no declara moneda** (muchos de ellos sí se recuperan del texto) y **55 con un problema real de precio o moneda** (16 precios en CUC, 5 en CUP y 34 en USD). De los 147, 25 siguen siendo utilizables porque la revisión manual recuperó el importe; los 122 restantes quedan sin precio.
- **CUP**: los 5 anuncios con precio en CUP quedan marcados y fuera de toda conversión y de toda estadística de precio.
- **EUR (n=3)**: se conservan en euros porque la descripción del vendedor lo dice literalmente, aunque en HogarEnCuba el título y el JSON-LD digan USD. `HEC1925` (620.000) y `HEC2258` (50.000) son fichas de HogarEnCuba y `cubisima_000018` (48.000) es de Cubisima, con el importe recuperado del texto. El conflicto se documenta como limitación y **no se interpretan** (n<10).
- **CUC**: 527 anuncios con precio; se valoran con paridad nominal declarada 1 CUC = 1 USD porque no hay tasa de mercado registrada para el CUC. Es una convención de cálculo, no una tasa, y no se presenta como conversión verificada.
- Conversiones USD/EUR: se aplican tasa informal y formal del registro del 15/10/2026 (USD 796 / 673; EUR 892 / 770). ElToque estaba bloqueado y la tasa no está actualizada al corte: queda como pendiente documentado, no como dato cerrado.

## 4. Resultados por pregunta de investigación

### 4.1 Precio central por fuente y moneda (pregunta secundaria 1)

| Fuente | Moneda | n | Mediana | Media | Mínimo | Máximo |
|---|---|---:|---:|---:|---:|---:|
| Cubisima | CUC | 527 | 25.000 | 52.228 | 100 | 800.000 |
| Cubisima | USD | 8 | 19.000 | 27.688 | 5.000 | 90.000 |
| Cubisima | EUR | 1 | 48.000 | 48.000 | 48.000 | 48.000 |
| HogarEnCuba | USD | 181 | 60.000 | 127.254 | 5.500 | 1.300.000 |
| HogarEnCuba | EUR | 2 | 335.000 | 335.000 | 50.000 | 620.000 |
| Revolico | USD | 691 | 25.000 | 49.903 | 111 | 900.000 |

La mediana es el centro robusto: las medias quedan muy por encima porque hay una cola de anuncios caros (hasta 1,3 millones en HogarEnCuba). Solo USD es comparable entre fuentes; las filas con n<10 (Cubisima USD n=8, EUR n=1 y n=2) se muestran por trazabilidad y no se interpretan.

### 4.2 Variación entre municipios (pregunta secundaria 2)

Municipios homologados (solo los 15 de La Habana; n≥5 por fuente y moneda; USD):

| Municipio | Revolico (n; mediana) | HogarEnCuba (n; mediana) |
|---|---|---|
| Playa | 134; 50.000 | 48; 142.500 |
| Plaza de la Revolución | 87; 45.000 | 38; 77.500 |
| Diez de Octubre | 95; 35.000 | 15; 55.000 |
| Habana del Este | 37; 25.000 | 11; 75.000 |
| Habana Vieja | 31; 28.000 | 6; 46.500 |
| Boyeros | 23; 23.500 | 6; 85.000 |
| Cerro | 30; 15.000 | 13; 21.000 |
| Centro Habana | 79; 15.000 | 19; 35.000 |
| Arroyo Naranjo | 33; 15.000 | 5; 20.000 |
| Marianao | 14; 13.250 | 7; 50.000 |
| La Lisa | 19; 13.000 | 6; 37.500 |
| Guanabacoa | 12; 8.500 | 3 (n<5) |
| San Miguel del Padrón | 6; 9.000 | — |

El orden de municipios es estable en Revolico (Playa y Plaza arriba; Guanabacoa, San Miguel del Padrón y La Lisa abajo) y HogarEnCuba repite los mismos barrios altos con importes mayores, pero la diferencia entre fuentes (por ejemplo, Playa 50.000 frente a 142.500) es **descriptiva, no causal**: refleja composición y selección de anuncios, no un precio único de mercado. Las zonas de Cubisima (Siboney, Miramar, Vedado, Alamar…) se reportan aparte, sin mezclarlas con municipios.

### 4.3 Habitaciones y precio (pregunta secundaria 3)

Correlación de Spearman descriptiva, por fuente y moneda:

| Fuente | Moneda | Habitaciones (rho; n) | Baños (rho; n) |
|---|---|---|---|
| HogarEnCuba | USD | 0,610; 181 | 0,731; 181 |
| Cubisima | CUC | 0,604; 527 | 0,676; 527 |
| Revolico | USD | 0,591; 492 | 0,567; 266 |
| Cubisima | USD | 0,488; 8 (exploratorio) | 0,830; 8 (exploratorio) |

Medianas observadas (solo grupos con n≥5; el detalle con n<5 queda en `outputs/preguntas/preguntas_resueltas_*.md`):

| Habitaciones | Revolico USD (n; mediana) | Cubisima CUC (n; mediana) | HogarEnCuba USD (n; mediana) |
|---|---|---|---|
| 1 | 50; 10.500 | 53; 10.000 | 9; 18.000 |
| 2 | 202; 20.000 | 173; 14.500 | 41; 30.000 |
| 3 | 158; 42.500 | 142; 35.000 | 41; 55.000 |
| 4 | 54; 70.000 | 82; 60.000 | 44; 87.500 |
| 5 | 11; 75.000 | 26; 92.500 | 15; 160.000 |
| 6 | 6; 132.500 | 6; 145.000 | 16; 90.000 |
| 7 | 5; 75.000 | 6; 147.500 | 4 (n<5) |
| 8+ | 4; 550.000 (n=4, no se interpreta) | 4; 250.000 (n=4, no se interpreta) | 5; 180.000 |

La asociación es positiva y consistente en las tres fuentes y en las dos variables: a más habitaciones y más baños, mayor precio. La correlación no implica causalidad y está parcialmente condicionada por la cobertura: en Revolico los baños se conocen en el 37,7 % de los anuncios y el subconjunto analizable sesga hacia fichas mejor descritas.

### 4.4 Características de las viviendas caras (pregunta secundaria 4)

Solo Cubisima publica características auxiliares; se compara el tercio superior de precio con el resto **dentro de CUC** (n=186 con precio ≥ 45.000 frente a n=341):

| Característica | % en el tercio superior | % en el resto | Diferencia (pp) |
|---|---:|---:|---:|
| Garaje | 65,6 | 18,8 | +46,8 |
| Jardín | 46,8 | 9,4 | +37,4 |
| Terraza | 54,8 | 26,1 | +28,7 |
| Patio | 68,3 | 53,1 | +15,2 |
| Piscina | 13,4 | 2,6 | +10,8 |
| Balcón | 31,7 | 31,7 | 0,0 |

Un 0 significa que la característica no fue declarada en la ficha, no que no exista. En USD no se calcula el tercio superior porque solo hay 8 anuncios de Cubisima con precio en USD.

### 4.5 Canales informales y fuentes estructuradas (pregunta secundaria 5)

| Canal | Moneda | Anuncios | Mediana | Con habitaciones | Con baños | Fecha de análisis |
|---|---|---:|---:|---:|---:|---:|
| Informal — Revolico | USD | 691 | 25.000 | 492 (71,2 %) | 266 (38,5 %) | 80,0 % |
| Estructurado — Cubisima | CUC | 527 | 25.000 | 527 (100 %) | 527 (100 %) | 100 % |
| Estructurado — HogarEnCuba | USD | 181 | 60.000 | 181 (100 %) | 181 (100 %) | 88,4 % |

Diferencias observables entre canales:

1. **Volumen y cobertura**: Revolico aporta 755 fichas con metadato pobre; las plataformas estructuradas aportan menos anuncios con metadato casi completo. Revolver la página de cada anuncio es lo que convierte un clasificado informal en una fuente utilizable.
2. **Precio**: las medianas USD de Revolico (25.000) y HogarEnCuba (60.000) difieren; la diferencia es de composición (HogarEnCuba publica viviendas más grandes y más caras) y no un "precio del canal".
3. **Moneda**: Revolico concentra la oferta en USD; Cubisima ofrece CUC masivo; HogarEnCuba casi solo USD. Solo USD es comparable entre canales.
4. **Transparencia de la oferta**: las zonas de Cubisima son más específicas (barrios turísticos), mientras que Revolico exige reconstruir el municipio desde el texto.
5. **EUR**: 2 fichas de HogarEnCuba y 1 de Cubisima; no se interpretan.

### 4.6 Conversión de moneda y tasas (pregunta secundaria 7)

- Tasas registradas: 15/10/2026 (USD informal 796, formal 673; EUR informal 892, formal 770); fuente ElToque bloqueada, valores manuales auditables.
- El mismo precio en USD cambia de valor equivalente según la tasa: la divergencia entre informal y formal es del orden del 18 % en USD y del 16 % en EUR. Es una aritmética de conversión, no una medida de mercado.
- CUC: 527 anuncios con paridad nominal 1 CUC = 1 USD, mediana equivalente 25.000 USD. No es tasa de mercado y no se usa como precio en dólares.
- EUR: 2 fichas de HogarEnCuba (mediana convertida 375.402 USD) y 1 de Cubisima (53.789 USD): ilustrativas, no estimaciones poblacionales.
- La tasa vigente está desactualizada respecto del corte (pendiente de valores verificados).

### 4.7 Agrupamiento de las viviendas (pregunta secundaria 6)

k-means (k=3) por moneda, sobre precio, habitaciones y banos, con casos completos (≥30 observaciones por moneda; EUR queda fuera con n=3). Los grupos se ordenan por mediana de precio:

| Moneda | Grupo | Anuncios | Mediana de precio | Mediana habitaciones | Mediana baños |
|---|---|---:|---:|---:|---:|
| CUC | Económico | 238 | 13.000 | 2 | 1 |
| CUC | Medio | 212 | 38.000 | 3 | 2 |
| CUC | Alto | 77 | 150.000 | 4,5 | 4 |
| USD | Económico | 245 | 30.000 | 2 | 1 |
| USD | Medio | 169 | 85.000 | 4 | 3 |
| USD | Alto | 24 | 550.000 | 7,5 | 7 |

El patrón es nítido y consistente entre monedas: el grupo alto concentra más habitaciones y más baños que el grupo económico, y el grupo económico son las viviendas más pequeñas. El cluster USD "alto" es pequeño (24 anuncios) y concentra los precios extremos (hasta 1,3 millones): se describe, no se generaliza.

La segmentación por terciles de precio (33/66) confirma el mismo gradiente dentro de cada moneda: en CUC el tercio alto son 171 anuncios (38 con 5+ habitaciones, mediana 150.000; 109 con 3-4, 72.000; 24 con ≤2, 60.000) y en USD 214 anuncios (57 con 5+, 200.000; 128 con 3-4, 105.000; 29 con ≤2, 80.000). Los perfiles con n<5 (por ejemplo, el grupo económico con 5+ habitaciones) no se interpretan.

### 4.8 Migración, oferta y demanda (pregunta secundaria 8)

Con los datos disponibles **no es posible medir** el efecto de la migración: la muestra de anuncios es transversal y las fechas útiles de Revolico son casi todas de agosto a octubre de 2026 (1 anuncio de mayo de 2025, 2 de agosto, 111 de septiembre y 488 de octubre de 2026 sobre 602 fechas de página). No hay serie temporal de precios ni de oferta, y por tanto no existe panel 2020-2026 que permita separar migración, crisis económica, desmonetización y tasa de cambio. Lo que sí puede afirmarse es que la evidencia transversal es **compatible** con la hipótesis de una oferta presionada: el grupo económico concentra 245 de los 438 casos completos en USD (mediana 30.000) y 238 de 527 en CUC (mediana 13.000), y en HogarEnCuba la media (127.254) está muy por encima de la mediana (60.000) por el peso de los anuncios caros. La verificación de esa hipótesis requiere la serie temporal que este proyecto no tiene.

### 4.9 Qué explica el precio y qué queda sin cobertura (pregunta secundaria 9)

- 1.410 de 1.532 anuncios (92,0 %) con precio de análisis; 1.358 con fecha de análisis; 1.434 con ubicación y 940 con municipio homologado; 1.305 con habitaciones, 1.062 con baños y 1.322 con al menos una de las dos variables de tamaño.
- Lo que el precio explica y los datos no cubren: el 100 % de las habitaciones y los banos no es alcanzable (en Revolico, 153 anuncios son inaccesibles y no tienen descripción, y otros anuncios publicados simplemente no mencionan la cantidad; el campo publicado solo trae habitaciones en 69 fichas y nunca trae banos, mientras el texto, el título o el enlace permiten obtener 528 habitaciones y 285 banos).
- La cobertura de la superficie no llega al 100 % en ninguna fuente, por lo que **no se usa como variable explicativa**.
- Las 14 fichas de alcance dudoso y las 122 sin precio verificable son el faltante principal: ninguna se resuelve por imputación.

## 5. Triangulación con entrevistas anónimas

Base: 10 entrevistas (E01–E10; 15/10/2026 a 19/10/2026) procesadas con `procesar_entrevistas.py`, que anonimiza, no persiste metadatos personales y codifica temas con palabras clave acento-insensibles. Salidas auditables: `outputs/entrevistas/entrevistas_codificadas_*.csv` (códigos C1–C7) y `resumen_entrevistas_*.md` (respuestas literales). Perfil: 4 propietarios, 2 inquilinos, 2 herederos, 1 asesor inmobiliario y 1 familiar de propietarios; viviendas de referencia en 10 de Octubre (5), Plaza de la Revolución (2), Centro Habana (2) y Playa (1). Es una muestra pequeña, no probabilística y autoseleccionada: describe percepciones y mecanismos, no prevalencias ni causalidad.

- **Migración**: las 10 respuestas la mencionan (C2 = 10/10) y 8 de 10 la nombran dentro del factor dominante (E02–E04 y E06–E09 la eligen como factor único o principal; E05 la combina priorizando la crisis económica; E01 señala solo la crisis; E10 señala los tres factores sin elegir uno). Mecanismo repetido: la emigración aumentó la oferta de casas para financiar la salida, la demanda local sin dinero cayó y la urgencia empujó los precios a la baja (E07: ventas "con todo dentro hasta por 4 mil dólares"; E09: caídas percibidas "hasta un 50 %"; E10: vender "para poder tener liquidez y solvencia para salir del país"). Son percepciones: el proyecto no tiene serie temporal y no puede medir ni refutar esa caída.
- **Evolución percibida desde 2020**: 7 de 10 describen descenso (E02–E04, E06–E09), 1 no distingue (E01), 1 percibe un periodo variable con posible revalorización (E05) y 1 un "aumento sin límites" por inflación (E10). Se reporta como disenso, sin promediar percepciones.
- **Urgencia y necesidad** (pregunta 9): 8 de 10 mencionan urgencia, necesidad de dinero o emigración como motivo de la reducción (E01–E04, E06, E07, E09, E10); 2 el estado o la ubicación (E05, E08). Coincide con C1 (necesidad o urgencia) presente en 9 de 10. La motivación no se observa en los anuncios y no se estima.
- **Ubicación**: 6 de 10 la nombran factor principal (E01, E02, E05, E06, E09, E10), 2 el estado constructivo (E03, E07) y 2 el tamaño (E04, E08). En los anuncios la dirección es la misma y medible (Revolico USD: Playa 50.000 con n=134 frente a Plaza 45.000 con n=87 y municipios bajos con n≥10), como asociación descriptiva, sin estimar cuánto aporta la ubicación.
- **Moneda y tasas**: 8 de 10 mencionan moneda o tasas (C3) y describen precios anclados en divisas con tasas que afectan sobre todo a la conversión a moneda nacional (E04: "la vivienda tiene un precio en usd y las tasas solo influyen para el cambio a mn"; E10: "todo se rige por la tasa de cambio"). En los datos, los precios utilizables están casi todos en divisas (880 USD, 527 CUC nominal, 3 EUR) y los 5 en CUP quedaron marcados como sospechosos: la percepción tiene contraparte en el registro.
- **Canales**: 4 de 10 prefieren grupos de Telegram/WhatsApp/Facebook (E01, E02, E08, E09), 4 intermediarios (E03, E04, E05, E10) y 2 plataformas tipo Revolico (E06, E07). La comparación de fuentes apunta en la misma dirección desde el otro lado: las plataformas estructuradas documentan mejor banos y zona que el clasificado informal.
- Frecuencias de código: C1 necesidad económica 9/10, C2 migración 10/10, C3 moneda y tasa 8/10, C4 canal de venta 4/10, C5 precio alto 7/10, C6 características 2/10, C7 municipio 10/10.
- El triángulo se queda en evidencia cualitativa: nunca se usa para estimar efectos ni para afirmar que la migración causó un porcentaje de cambio en los precios.

## 6. Limitaciones

1. **Anuncios ≠ transacciones**: se observan precios pedidos, no precios pactados; no hay fecha de operación ni superficies verificadas.
2. **Sin serie temporal**: 601 de 602 fechas útiles de Revolico son de agosto a octubre de 2026; no hay panel 2020-2026 y no se puede medir evolución de precios ni el efecto de la migración.
3. **Sesgo de disponibilidad en Revolico**: 153 de 755 anuncios ya no son accesibles (80 despublicados, 73 eliminados). No se descartan: quedan marcados con `fecha_ultima_disponibilidad`, `ventana_despublicacion` y `justificacion_disponibilidad`; la desaparición solo puede acotarse al intervalo 29/09–18/10/2026.
4. **Cobertura parcial de habitaciones y banos**: el techo lo fija el texto del anuncio (153 inaccesibles y descripciones que omiten la cantidad). La cadena de decisión es descripción → título → campo publicado → enlace; 72 anuncios con cantidades discrepantes quedan marcados en `conflicto_detalle` sin resolverse. No se imputa nada.
5. **Municipios y zonas no son equivalentes**: solo 940 fichas tienen municipio homologado (Revolico 657, HogarEnCuba 183, Cubisima 100, y en Cubisima el nombre de la zona coincide con un municipio, no con una municipalización). Las zonas de Cubisima se analizan aparte.
6. **Superficie (m²) excluida**: 0 % en Revolico y Cubisima, 9/183 (4,9 %) en HogarEnCuba.
7. **Precios en CUP (5) y EUR (3) no interpretables**: los CUP quedan como sospechosos y los EUR se conservan por literalidad de la descripción, en conflicto con el JSON-LD de HogarEnCuba.
8. **CUC convertido por paridad nominal**: no existe tasa de mercado registrada; la conversión 1:1 es una convención declarada.
9. **Tasas desactualizadas**: registro del 15/10/2026 con ElToque bloqueado; las conversiones USD/EUR quedan con esa fecha explícita y son ilustrativas.
10. **122 anuncios sin precio verificable** (69 sin precio en texto, 16 que solo repiten el precio ya marcado, 14 no verificables, 8 no disponibles, 5 en CUP, 4 despublicados, 3 ambiguos, 1 error, 1 moneda ambigua, 1 valor improbable) y **14 de alcance dudoso**: son el faltante principal y no se resuelven por imputación.
11. **Alcance excluido y su tratamiento**: 34 fichas quedan fuera del maestro (6 no residenciales, 13 fuera de La Habana, 15 no vivienda); la lista de las 14 dudosas conservadas está en `revision_manual/alcance_dudoso.csv`.
12. **Sin scraping de Revolico ni de redes sociales**: se usa HTML guardado; Facebook y Telegram solo han aportado evidencia manual y la encuesta anónima.
13. **Muestra de entrevistas no probabilística**: describe mecanismos y percepciones; no estima prevalencias ni efectos.

## 7. Entregables del proyecto

| Carpeta | Contenido |
|---|---|
| `outputs/integracion/` | Maestro integrado (1.532 filas) y registro de integración |
| `outputs/limpieza_integrada/` | Maestro depurado con columnas de análisis (no sobrescribe los campos publicados) |
| `outputs/conversiones/` | Precios convertidos con tasa, fecha y método (informal, formal y nominal CUC) |
| `outputs/comparativos/` | Cobertura por fuente, comparativo por canal y sus gráficos |
| `outputs/segmentacion/` | Segmentación por terciles (33/66) y perfiles por tamaño |
| `outputs/clustering/` | k-means por moneda, centroides y dispersión de grupos |
| `outputs/visualizaciones/` | 8 gráficos de síntesis y resumen tabular |
| `outputs/entrevistas/` | Entrevistas codificadas (E01–E10) y resumen con citas literales |
| `outputs/validacion/` | Revisión de precios, lista de pendientes y evidencias de revisión |
| `outputs/preguntas/` | Respuestas a las 9 preguntas con tablas y notas de interpretación |
| `revision_manual/` | Decisiones manuales auditadas: precios bajos, precios ausentes, exclusiones de alcance, alcance dudoso |

Reproducibilidad: `python cifras_control.py` imprime todas las cifras de control de este documento contra el maestro vigente; `python auditoria_revolico.py` verifica la consistencia de la extracción de Revolico; `python control_calidad.py` revisa compilación, documentación y estado de Git; `python -m unittest discover -s tests -t .` ejecuta la batería de pruebas (68 en verde).

## 8. Pendientes

1. **Tasas verificadas** (bloqueante para cualquier cifra en dólares convertidos): incorporar valores confirmados por el usuario con `tasas_cambio.py --usd-informal ... --fuente ...` y regenerar conversiones y gráficos.
2. **Revisión conjunta de los 122 precios pendientes** y de las 14 fichas de alcance dudoso: decidir caso por caso sin imputar.
3. **Informe final**: redacción académica con discusión, limitaciones y referencias, pendiente de autorización expresa del usuario.
