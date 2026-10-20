# Mercado inmobiliario de La Habana: análisis reproducible de anuncios

Proyecto académico que analiza el mercado inmobiliario de La Habana a partir de anuncios reales de tres fuentes cubanas (**Revolico**, **Cubisima** y **HogarEnCuba**), complementados con **10 entrevistas anónimas** y con un registro manual de **tasas de cambio**.

- **Tema:** precio de la vivienda y sus determinantes observables (tamaño, zona, canal, moneda), en el contexto de la crisis económica, la desmonetización del CUC y la migración.
- **Corte de datos:** 19/10/2026 · **Revisión del estado:** 20/10/2026
- **Base de análisis:** 1.532 anuncios (Revolico 755, Cubisima 594, HogarEnCuba 183) con 1.410 precios utilizables (92,0 %).
- **Naturaleza:** asociación descriptiva y reproducible. No se afirma causalidad y no se imputan valores ausentes.

> El documento de resultados vigente es [`informe_preliminar.md`](informe_preliminar.md). El informe final académico queda pendiente de autorización expresa.

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
| Anuncios en el maestro | 1.532 (0 IDs y 0 URLs duplicados) |
| Precios utilizables | 1.410 (92,0 %) |
| Sin precio verificable | 122 (con motivo registrado) |
| Moneda de análisis | USD 880 · CUC 527 · EUR 3 · sin moneda 122 |
| Municipios homologados | 940 (solo los 15 de La Habana) |
| Anuncios de Revolico inaccesibles | 153 (80 despublicados, 73 eliminados) |
| Fichas excluidas del alcance | 34 (6 no residenciales, 13 fuera de La Habana, 15 no vivienda) |
| Fichas de alcance dudoso conservadas | 14 (listadas en `revision_manual/alcance_dudoso.csv`) |
| Entrevistas codificadas | 10 (E01–E10, 15–19/10/2026) |
| Pruebas automáticas | 68 en verde (`python -m unittest discover -s tests -t .`) |

Detalle por pregunta, tabla y gráfico: `outputs/preguntas/preguntas_resueltas_*.md`.

## 3. Estructura del repositorio

```
.
├── AGENTS.md                       reglas de trabajo del proyecto
├── README.md                       este documento
├── informe_preliminar.md           informe de resultados consolidado (preliminar)
├── preguntas_investigacion.md      formulación de las preguntas
├── data_dictionary.md              columnas, formatos y políticas de cada campo
├── fuentes_datos.md                estado de verificación de cada fuente
├── matriz_variables_fuentes.md     qué variable publica cada fuente
├── cuestionario_entrevistas.md     instrumento de entrevista
├── diseno_encuesta_online.md       formulario equivalente para Google Forms
├── ubicaciones.py                  homologación de los 15 municipios de La Habana
├── precio_moneda.py                librería de parseo conservador de importes y monedas
├── cifras_control.py               todas las cifras de control del maestro vigente
├── auditoria_revolico.py           auditoría de consistencia de la extracción de Revolico
├── <scripts del pipeline>          ver catálogo en la sección 5
├── tests/                          pruebas de precio/moneda, alcance y ubicaciones
├── revision_manual/                decisiones manuales auditadas (CSV)
├── data/                           respaldos locales, no versionados
└── outputs/                        resultados derivados, no versionados
```

## 4. Pipeline y orden de ejecución

El pipeline es **no destructivo**: cada etapa escribe en `outputs/` con marca de tiempo y nunca sobrescribe un archivo original.

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
| `clustering_viviendas.py` | k-means (k=3) por moneda sobre precio, habitaciones y banos |
| `visualizaciones_fuentes.py` | 8 gráficos de síntesis y resumen tabular |
| `analisis_preguntas.py` | Respuestas tabuladas a las 9 preguntas con notas de interpretación |
| `procesar_entrevistas.py` | Anonimización y codificación (C1–C7) de las respuestas de la encuesta |

### Control
| Script | Función |
|---|---|
| `cifras_control.py` | Cifras de control del maestro vigente (solo lectura) |
| `auditoria_revolico.py` | Auditoría de consistencia de la extracción de Revolico (solo lectura) |
| `control_calidad.py` | Control de calidad: compilación, artefactos de texto, tablas y estado de Git |
| `generar_alcance_dudoso.py` | Regenera `revision_manual/alcance_dudoso.csv` desde el maestro |
| `generar_precios_pendientes.py` | Regenera la lista de precios pendientes con motivo y acción sugerida |
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
| `exclusiones_alcance.csv` | 28 exclusiones de alcance con URL, motivo y evidencia |
| `alcance_dudoso.csv` | 14 anuncios de uso mixto o dudoso conservados en el maestro |

### `outputs/` (resultados derivados, no versionados)
`integracion/`, `limpieza_integrada/`, `conversiones/`, `comparativos/`, `segmentacion/`, `clustering/`, `visualizaciones/`, `entrevistas/`, `validacion/`, `preguntas/`, `historico/`. Todos los archivos llevan marca de tiempo (`*_AAAAMMDD_HHMMSS.*`); las dos últimas ejecuciones se conservan para comparación.

### `data/` (respaldos locales, no versionados)
`raw/` con los CSV originales y `hash_inventario.csv`; `tasas/` con el registro de tasas; `entrevistas/` con la exportación original de la encuesta (contiene datos personales identificables: **nunca se versiona ni se publica**).

## 7. Decisiones metodológicas aplicadas

1. **Un anuncio no es una transacción.** La unidad observada es el anuncio; los precios son pedidos, no pactos.
2. **Ningún valor se imputa.** Se distinguen *dato inexistente*, *dato no extraído* y *dato pendiente de revisión manual* mediante `precio_sospechoso`, `veredicto_revision` y `origen_precio`.
3. **Dos columnas, dos realidades.** `precio_original`/`moneda` conservan lo publicado; `precio_analisis`/`moneda_analisis` usan la reextracción manual verificada y excluyen lo sospechoso. El campo publicado nunca se corrige.
4. **Moneda antes que comparación.** Solo se comparan importes dentro de la misma moneda; el CUC se convierte con paridad nominal declarada (no es tasa de mercado) y el EUR se conserva por literalidad de la descripción, aunque el JSON-LD de HogarEnCuba diga USD.
5. **Municipios homólogos.** Solo los 15 municipios de La Habana; las zonas o barrios de Cubisima se analizan aparte y no se imputan como municipio.
6. **Umbrales de publicación.** En gráficos se excluyen monedas con n<5, combinaciones fuente-moneda con n<10 y grupos con n<5, y esas exclusiones se anotan en la propia figura.
7. **Sin causalidad.** Todo resultado se redacta como asociación descriptiva; la migración no se atribuye porcentualmente porque no hay serie temporal.
8. **Superficie fuera del análisis.** Ninguna fuente la publica de forma sistemática (HogarEnCuba: 9/183).
9. **Sin scraping de redes sociales.** Facebook y Telegram solo aportan evidencia manual y la encuesta anónima.

## 8. Control, pruebas y trazabilidad

```powershell
python cifras_control.py        # cifras de control contra el maestro vigente
python auditoria_revolico.py    # consistencia de la extracción de Revolico
python control_calidad.py       # compilación, artefactos de texto, tablas y estado de Git
python -m unittest discover -s tests -t .   # 68 pruebas
```

- Cada anuncio tiene `id_maestro` único y conserva `id_local`, `url`, `snapshot_origen`, `origen_precio`, `origen_ubicacion`, `origen_habitaciones`, `origen_banos` y `evidencia_*` para reconstruir de dónde salió cada valor.
- Las decisiones manuales viven en `revision_manual/` y se aplican por URL, de modo que la auditoría puede rehacer el camino.
- Los archivos de `outputs/` no se versionan: se regeneran con los scripts del pipeline.

## 9. Estado de Git

Se versionan código, documentación, pruebas y las decisiones manuales auditadas (`revision_manual/`). **No** se versionan `data/`, `outputs/`, el HTML guardado de Revolico ni los archivos temporales.

**Rama de trabajo:** `main`, con historial público; los cambios de auditoría se registran en commits separados de los cambios de contenido.

## 10. Limitaciones conocidas

1. Sin serie temporal de precios: 601 de 602 fechas útiles de Revolico son de agosto a octubre de 2026. No hay panel 2020-2026.
2. Sesgo de disponibilidad: 153 de 755 anuncios de Revolico ya no son accesibles; se marcan con su ventana de despublicación.
3. Cobertura parcial de habitaciones (69,9 %) y banos (37,7 %) en Revolico; 72 anuncios con cantidades discrepantes quedan sin resolver.
4. 122 anuncios sin precio verificable y 14 de alcance dudoso: el faltante principal, que no se resuelve por imputación.
5. Tasas desactualizadas (registro del 15/10/2026; ElToque bloqueado): las conversiones son ilustrativas hasta que se incorporen valores verificados.
6. Precios en CUP (5) y EUR (3) no interpretables por volumen o por conflicto de fuente.
7. Muestra de entrevistas pequeña, no probabilística y autoseleccionada: describe mecanismos, no prevalencias.

## 11. Pendientes

1. **Tasas verificadas** (bloqueante para cifras convertidas): `python tasas_cambio.py --usd-informal <valor> --fuente "<fuente>"` y regenerar conversiones y gráficos.
2. **Revisión conjunta** de los 122 precios pendientes y de las 14 fichas de alcance dudoso, sin imputar.
3. **Informe final**: redacción académica con discusión, limitaciones y referencias, pendiente de autorización expresa.
