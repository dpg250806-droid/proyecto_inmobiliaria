# Mercado inmobiliario de La Habana: análisis reproducible de anuncios

Proyecto académico que analiza el mercado inmobiliario de La Habana a partir de anuncios reales de tres fuentes cubanas (**Revolico**, **Cubisima** y **HogarEnCuba**), complementados con **10 entrevistas anónimas** y con un registro manual de **tasas de cambio**.

- **Tema:** precio de la vivienda y sus determinantes observables (tamaño, zona, canal, moneda), en el contexto de la crisis económica, la desmonetización del CUC y la migración.
- **Corte de datos:** 19/10/2026 · **Tasas de cambio:** 20/10/2026 · **Auditoría técnica:** 21/10/2026
- **Base de análisis:** 1.516 anuncios (Revolico 748, Cubisima 585, HogarEnCuba 183) con 1.404 precios utilizables (92,6 %).
- **Naturaleza:** asociación descriptiva y reproducible. No se afirma causalidad y no se imputan valores ausentes.

> [`informe_preliminar.md`](informe_preliminar.md) conserva resultados de una ejecución anterior y está marcado como pendiente de regeneración bajo los umbrales de publicación vigentes. No debe citarse como resultado actualizado. El informe final académico queda pendiente de autorización expresa.

---

## 1. Preguntas de investigación

**Principal.** ¿Qué características de una vivienda están relacionadas con su precio de venta?

**Secundarias.**

1. ¿Cuál es el precio promedio de las viviendas?
2. ¿Cómo varían los precios entre municipios?
3. ¿Existe relación entre habitaciones y precio?
4. ¿Qué características aparecen con mayor frecuencia en las viviendas de precios altos?
5. ¿Qué diferencias observables existen entre canales informales y fuentes estructuradas?
6. ¿Se pueden agrupar las viviendas en diferentes tipos según sus características?
7. ¿Cómo cambia el precio equivalente al convertir USD, CUP y EUR con tasas informales y formales?
8. ¿Qué influencia ha tenido la migración en la oferta, la demanda y los precios entre 2020 y 2026?
9. ¿Qué parte del precio puede explicarse con los datos disponibles y qué queda sin cobertura?

El detalle de la formulación está en [`preguntas_investigacion.md`](preguntas_investigacion.md); las respuestas tabuladas, con sus notas de interpretación, se regeneran en `outputs/preguntas/`.

## 2. Estado actual en cifras

| Indicador | Valor |
|---|---|
| Anuncios en el maestro | 1.516 (0 IDs y 0 URLs duplicados) |
| Precios utilizables | 1.404 (92,6 %) |
| Sin precio verificable | 112 (con motivo registrado) |
| Moneda de análisis | USD 885 · CUC 515 · EUR 4 · sin moneda 112 |
| Municipios homologados | 931 (solo los 15 de La Habana) |
| Anuncios de Revolico inaccesibles | 153 (80 despublicados, 73 eliminados) |
| Fichas excluidas del alcance | 50: 22 no residenciales/alquileres y 28 fuera de alcance (13 fuera de La Habana y 15 no vivienda) |
| Fichas de alcance dudoso | 14, **incluidas** por decisión de la investigadora (venta de inmueble) y marcadas en `alcance_dudoso`; la sensibilidad de retirarlas no mueve ninguna mediana (0,00 %) |
| Revisión de precios < 1.000 | 23 anuncios revisados uno a uno: 9 alquileres retirados, 9 sin precio verificable, 4 despublicados, 1 reextraído (12.500 USD) |
| Segunda pasada sobre los 134 sin precio | 15 precios recuperados del texto (12 USD, 4.500-600.000 USD, 125.000 EUR, 7.500 USD por convención de millares) y 7 anuncios retirados por no ser oferta de venta de vivienda |
| Sensibilidad de las 50 exclusiones (22/10/2026) | Conservar los 9 alquileres y los 7 no residenciales **no mueve ninguna mediana** (0,00 %); solo baja el percentil 5 de Cubisima CUC un 9 % (5.000 → 4.550). Tabla en `outputs/auditoria/` |
| Refresco de disponibilidad de Revolico (22/10/2026) | **No realizado**: HTTP 403 (Cloudflare) en las 78 fichas alcanzadas; se abortó sin forzar el sitio. El estado verificable sigue siendo el del snapshot del 18/10/2026 |
| Tasas registradas | 20/10/2026 (USD 815 informal / 710,50 formal; EUR 910 / 796,26) |
| Entrevistas codificadas | 10 (E01–E10, 15–19/10/2026) |
| Pruebas automáticas | 74 en verde (`python -m unittest discover -s tests -t .`) |
| Scrapers (prueba acotada) | Cubisima HTTP 200 (24 anuncios en 1 de 25 páginas); HogarEnCuba 13 fichas sin fallos (1 de 10 páginas); Revolico HTTP 403 en línea también en las fichas individuales desde el 22/10: se trabaja con el HTML guardado |

Detalle por pregunta, tabla y gráfico: `outputs/preguntas/preguntas_resueltas_*.md`.

## 3. Estructura del repositorio

```
.
├── AGENTS.md                       reglas de trabajo del proyecto
├── README.md                       este documento
├── requirements.txt                versiones de dependencias probadas en este entorno
├── informe_preliminar.md           informe de resultados consolidado (preliminar)
├── preguntas_investigacion.md      formulación de las preguntas
├── data_dictionary.md              columnas, formatos y políticas de cada campo
├── fuentes_datos.md                estado de verificación de cada fuente
├── fuentes_externas.md             triangulación con la documentación publicada (prensa y análisis)
├── matriz_variables_fuentes.md     qué variable publica cada fuente
├── cuestionario_entrevistas.md     instrumento de entrevista
├── diseno_encuesta_online.md       formulario equivalente para Google Forms
├── ubicaciones.py                  homologación de los 15 municipios de La Habana
├── precio_moneda.py                librería de parseo conservador de importes y monedas
├── cifras_control.py               todas las cifras de control del maestro vigente
├── salidas.py                      rutas fechadas para no reemplazar gráficos/reportes
├── auditoria_revolico.py           auditoría de consistencia de la extracción de Revolico
├── <scripts del pipeline>          ver catálogo en la sección 5
├── tests/                          pruebas de precio/moneda, alcance y ubicaciones
├── revision_manual/                decisiones manuales auditadas (CSV)
├── data/                           respaldos locales, no versionados
└── outputs/                        resultados derivados, no versionados
```

## 4. Pipeline y orden de ejecución

El pipeline es **no destructivo**: cada etapa escribe en `outputs/` con marca de tiempo y nunca sobrescribe un archivo original.
Las dependencias de Python están fijadas en `requirements.txt` con las versiones disponibles y probadas en esta auditoría (Python 3.14). Para preparar un entorno:

```powershell
python -m pip install -r requirements.txt
```

```powershell
# 1. Extracción (solo si hay red y autorización; Revolico usa el HTML guardado)
python scraper_cubisima_online.py
python scraper_hogarencuba.py
python extraer_metadatos_revolico.py      # municipio, fecha y descripción por anuncio
python extraer_detalle_anuncios_revolico.py # habitaciones y banos desde el texto

# 2. Precios, monedas y revisión manual
python revisar_precios_ausentes.py
python revisar_descripciones_precios_bajos.py
python aplicar_revision_manual.py

# 3. Integración y limpieza
python integrar_fuentes.py                 # maestro con exclusiones de alcance y homologación
python limpieza_integrada.py              # columnas de análisis sin tocar campos publicados

# 4. Tasas y conversiones
python tasas_cambio.py --usd-informal 796 --fuente "registro manual 15/10/2026"
python convertir_precios_tasas.py

# 5. Análisis
python comparativo_fuentes.py
python segmentacion_viviendas.py
python clustering_viviendas.py
python visualizaciones_fuentes.py
python analisis_preguntas.py
python procesar_entrevistas.py

# 6. Control y pruebas
python cifras_control.py
python auditoria_revolico.py
python control_calidad.py
python -m unittest discover -s tests -t .
```

## 5. Catálogo de scripts

### Captura y preprocesamiento
| Script | Función |
|---|---|
| `scraper_revolico.py` | Scraper híbrido del listado de Revolico (bloqueado en línea: se trabaja con HTML guardado) |
| `scraper_cubisima.py`, `scraper_cubisima_online.py` | Captura no destructiva de Cubisima (La Habana) |
| `scraper_hogarencuba.py` | Captura reproducible de HogarEnCuba |
| `reprocesar_cubisima.py`, `reprocesar_hogarencuba.py` | Copias corregidas de snapshots, sin alterar el original |
| `limpiar_revolico.py`, `procesar_anuncios_revolico.py` | Limpieza y tipificación del dataset de Revolico |
| `eda_revolico.py` | EDA de solo lectura |

### Extracción de detalle (Revolico)
| Script | Función |
|---|---|
| `extraer_metadatos_revolico.py` | Municipio, fecha (`updatedOnByUser`) y descripción de cada anuncio |
| `extraer_detalle_anuncios_revolico.py` | Habitaciones y banos leídos del texto, con conflictos marcados |
| `leer_paginas_revolico.py`, `inspeccionar_revolico.py`, `buscar_datos_ocultos_revolico.py`, `diagnostico_json_revolico.py` | Inspección de páginas y del JSON-LD |

### Precios, monedas y revisión
| Script | Función |
|---|---|
| `precio_moneda.py` | Parseo conservador de importes y monedas (`precio_analisis`, `detalle_analisis`) |
| `tasas_cambio.py` | Registro manual de tasas USD/EUR/CUC → CUP (informal y formal) con fecha y fuente |
| `convertir_precios_tasas.py` | Conversiones con tasa, fecha y método; paridad nominal declarada para CUC |
| `revisar_precios_ausentes.py` | Búsqueda de precios ausentes en título, descripción y página |
| `revisar_descripciones_precios_bajos.py` | Revisión uno a uno de precios sospechosos bajos (<100) |
| `generar_revision_precios_bajos.py` | Genera la lista de precios bajos pendientes |
| `aplicar_revision_manual.py`, `actualizar_banos_hogarencuba.py`, `validar_hogarencuba.py` | Aplican correcciones manuales verificadas |

### Integración y análisis
| Script | Función |
|---|---|
| `integrar_fuentes.py` | Maestro integrado: exclusiones de alcance, homologación de municipios y columnas de análisis |
| `ubicaciones.py` | Homologación de los 15 municipios de La Habana |
| `limpieza_integrada.py` | Deriva columnas de análisis sin sobrescribir los campos publicados |
| `comparativo_fuentes.py` | Cobertura publicada vs. de análisis, comparativo por canal y sus gráficos |
| `segmentacion_viviendas.py` | Segmentación por terciles de precio (33/66) y perfiles por tamaño |
| `clustering_viviendas.py` | k-means (k=3) por moneda sobre log(precio), habitaciones y banos, con reinicios y prueba de estabilidad |
| `visualizaciones_fuentes.py` | 8 gráficos de síntesis y resumen tabular |
| `grafico_contraste_externo.py` | Contraste gráfico de nuestras medianas por municipio frente al promedio orientativo de la fuente externa |
| `analisis_preguntas.py` | Respuestas tabuladas a las 9 preguntas con notas de interpretación |
| `procesar_entrevistas.py` | Anonimización y codificación (C1–C7) de las respuestas de la encuesta |

### Control
| Script | Función |
|---|---|
| `cifras_control.py` | Cifras de control del maestro vigente (solo lectura) |
| `auditoria_revolico.py` | Auditoría de consistencia de la extracción de Revolico (solo lectura) |
| `control_calidad.py` | Control de calidad: compilación en memoria, documentación, hashes de datos y estado de Git |
| `generar_alcance_dudoso.py` | Regenera `revision_manual/alcance_dudoso.csv` desde el maestro |
| `generar_precios_pendientes.py` | Regenera la lista de precios pendientes con motivo y acción sugerida |
| `generar_precios_bajos_1000.py` | Regenera `revision_manual/precios_bajos_1000.csv` (veredictos manuales de la revisión de precios < 1.000) |
| `generar_precios_pendientes_recuperados.py` | Regenera `revision_manual/precios_pendientes_recuperados.csv` (15 precios recuperados y 7 anuncios de objeto no residencial) |
| `revisar_precios_pendientes_texto.py` | Rastrea en el texto ya descargado los montos declarados en los anuncios sin precio |
| `revisar_precios_bajos_1000.py` | Consulta la ficha individual de los anuncios con precio < 1.000 y extrae los montos del texto |
| `auditar_alquileres.py` | Detecta alquileres y permutas publicados en los catálogos de venta |
| `sensibilidad_exclusiones.py` | Comprueba el efecto de retirar alquileres y anuncios no residenciales sobre medianas y percentiles (solo lectura) |
| `tests/` | Pruebas de precio/moneda, exclusiones de alcance y homologación de municipios |

## 6. Datos y artefactos

### CSV de la raíz (muestras e insumos del pipeline, versionados)
| Archivo | Contenido |
|---|---|
| `anuncios_revolico_procesados.csv` | Anuncios de Revolico ya tipificados y con precio publicado |
| `viviendas_revolico_candidatas.csv` | Candidatas a vivienda tras la tipificación |
| `anuncios_revolico_revisar.csv` | Anuncios que requieren revisión manual |
| `anuncios_revolico_excluidos.csv` | Anuncios excluidos por la tipificación |
| `enlaces_anuncios_revolico.csv` | URLs del listado guardado |
| `datos_revolico_json.csv` | Extracción diagnóstica del JSON-LD de una muestra (no es una fuente de precio) |
| `viviendas_cubisima.csv` | Copia local del snapshot de Cubisima (ignorada por Git: se regenera) |

### `revision_manual/` (decisiones auditadas, versionadas)
| Archivo | Contenido |
|---|---|
| `precios_bajos.csv` | 37 precios revisados uno a uno contra la descripción |
| `precios_ausentes.csv` | 142 veredictos de la búsqueda de precios ausentes |
| `precios_bajos_1000.csv` | 23 anuncios con precio < 1.000 o alquileres, revisados contra la ficha individual (9 alquileres, 9 sin precio verificable, 4 despublicados, 1 reextraído) |
| `precios_pendientes_recuperados.csv` | Segunda pasada sobre los 134 anuncios sin precio: 15 precios recuperados con su cita literal y 7 anuncios que no son oferta de venta de vivienda |
| `exclusiones_alcance.csv` | 28 exclusiones de alcance con URL, motivo y evidencia |
| `alcance_dudoso.csv` | 14 anuncios de uso mixto o dudoso **incluidos** en el análisis por decisión (20/10/2026), con motivo, evidencia, decisión y advertencia de interpretación |

### `outputs/` (resultados derivados, no versionados)
`integracion/`, `limpieza_integrada/`, `conversiones/`, `comparativos/`, `segmentacion/`, `clustering/`, `visualizaciones/`, `auditoria/`, `entrevistas/`, `validacion/`, `preguntas/`, `historico/`. Las salidas nuevas llevan marca de tiempo y no reemplazan archivos existentes; las ejecuciones históricas se conservan.

### `data/` (respaldos locales, no versionados)
`raw/` con los CSV originales y `hash_inventario.csv`; `tasas/` con el registro de tasas; `entrevistas/` con la exportación original de la encuesta (contiene datos personales identificables: **nunca se versiona ni se publica**).

## 7. Decisiones metodológicas aplicadas

1. **Un anuncio no es una transacción.** La unidad observada es el anuncio; los precios son pedidos, no pactos.
2. **Ningún valor se imputa.** Se distinguen *dato inexistente*, *dato no extraído* y *dato pendiente de revisión manual* mediante `precio_sospechoso`, `veredicto_revision` y `origen_precio`.
3. **Dos columnas, dos realidades.** `precio_original`/`moneda` conservan lo publicado; `precio_analisis`/`moneda_analisis` usan la reextracción manual verificada y excluyen lo sospechoso. El campo publicado nunca se corrige.
4. **Moneda antes que comparación.** Solo se comparan importes dentro de la misma moneda; el CUC se convierte con paridad nominal declarada (no es tasa de mercado) y el EUR se conserva por literalidad de la descripción, aunque el JSON-LD de HogarEnCuba diga USD. Las tasas USD/EUR son las del 20/10/2026 (ElToque, leídas a mano porque el acceso automático está bloqueado) y toda cifra convertida cita esa fecha.
5. **Municipios homólogos.** Solo los 15 municipios de La Habana; las zonas o barrios de Cubisima se analizan aparte y no se imputan como municipio.
6. **Umbrales de publicación.** En tablas y gráficos de precios se excluyen monedas con n<5, combinaciones fuente-moneda con n<10 y grupos con n<5; las exclusiones se anotan cuando la salida permite mostrarlas.
7. **Sin causalidad.** Todo resultado se redacta como asociación descriptiva; la migración no se atribuye porcentualmente porque no hay serie temporal.
8. **Superficie fuera del análisis.** Ninguna fuente la publica de forma sistemática (HogarEnCuba: 9/183).
9. **Sin scraping de redes sociales.** Facebook y Telegram solo aportan evidencia manual y la encuesta anónima.
10. **Alcance dudoso incluido, no oculto.** Los 14 anuncios de venta de inmueble con uso mixto o dudoso se mantienen en el análisis (decisión de la investigadora, 20/10/2026), marcados en `alcance_dudoso` y con una prueba de sensibilidad que se publica: ninguna mediana se mueve.

## 8. Control, pruebas y trazabilidad

```powershell
python cifras_control.py        # cifras de control contra el maestro vigente
python auditoria_revolico.py    # consistencia de la extracción de Revolico
python control_calidad.py       # compilación en memoria, documentación, inventario y estado de Git
python -m unittest discover -s tests -t .   # 74 pruebas
```

- Cada anuncio tiene `id_maestro` único y conserva `id_local`, `url`, `snapshot_origen`, `origen_precio`, `origen_ubicacion`, `origen_habitaciones`, `origen_banos` y `evidencia_*` para reconstruir de dónde salió cada valor.
- Las decisiones manuales viven en `revision_manual/` y se aplican por URL, de modo que la auditoría puede rehacer el camino.
- Los archivos de `outputs/` no se versionan: se regeneran con los scripts del pipeline.

## 9. Estado de Git

Se versionan código, documentación, pruebas y las decisiones manuales auditadas (`revision_manual/`). **No** se versionan `data/`, `outputs/`, el HTML guardado de Revolico ni los archivos temporales.

**Rama de trabajo:** `main`, con historial público; los cambios de auditoría se registran en commits separados de los cambios de contenido.

## 10. Limitaciones conocidas

1. Sin serie temporal de precios: las 595 fechas de actualización disponibles en Revolico van de mayo de 2025 a octubre de 2026; no hay panel 2020-2026.
2. Sesgo de disponibilidad: 153 de 748 anuncios de Revolico ya no son accesibles; se marcan con su ventana de despublicación.
3. Cobertura parcial de habitaciones (70,3 %) y baños (38,0 %) en el dato de análisis de Revolico; 72 anuncios con cantidades discrepantes quedan sin resolver.
4. 112 anuncios sin precio verificable: es el faltante principal y no se resuelve por imputación (quedan listados con motivo y acción sugerida en `outputs/validacion/`).
5. Tasas de referencia, no operadas: el registro es del 20/10/2026 y se leyó de ElToque por transcripción manual (el acceso automático devuelve HTTP 403); el euro varió durante el día y se toma la cifra de las 17:00.
6. Precios en CUP (3) sospechosos y EUR (4) conservados por literalidad; EUR queda por debajo del umbral de publicación.
7. Muestra de entrevistas pequeña, no probabilística y autoseleccionada: describe mecanismos, no prevalencias.
8. Las 14 fichas de alcance dudoso pueden tener un precio que incluye tierra, licencia o equipamiento de negocio: se mantienen, se marcan y se prueban.
9. El catálogo de venta está contaminado: nueve anuncios eran alquileres (con el precio de la renta mensual), siete no eran oferta de venta de vivienda (productos, anuncios de agencia, una demanda de compra, un restaurante) y se retiraron; no se puede descartar que queden casos similares por encima de 1.000.
10. Cuatro de las siete fuentes externas contrastadas tienen interés comercial: se citan como comentario de mercado, no como medición (`fuentes_externas.md`).

## 11. Pendientes

1. ~~Tasas verificadas~~ — resuelto el 20/10/2026 (registro actualizado, conversiones y gráficos regenerados).
2. **Revisión de los 112 precios pendientes**, sin imputar: la lista con motivo y acción sugerida está en `outputs/validacion/precios_pendientes_actualizado_*.csv`. En su mayoría el vendedor nunca publicó un precio.
3. **Informe final**: redacción académica con discusión, limitaciones y referencias, pendiente de autorización expresa.
