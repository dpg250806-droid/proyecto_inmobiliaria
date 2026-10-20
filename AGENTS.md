# AGENTS.md

## Alcance

Este archivo define reglas para trabajar en el proyecto inmobiliario basado en anuncios de Revolico y fuentes complementarias.

## Tematica y fecha de inicio

- Tema: mercado inmobiliario cubano, con enfasis en La Habana.
- Enfoque: relacion entre precio, características de la vivienda, moneda, tasas de cambio, migracion y crisis economica.
- Fecha de inicio del tema y las preguntas: 29 de septiembre de 2026.
- Las preguntas se responderan con datos recopilados, procesamiento reproducible y encuestas anonimas.

## Preguntas de investigacion

Pregunta principal:
¿Qué características de una vivienda estan relacionadas con su precio de venta?

Preguntas secundarias:
1. ¿Cuál es el precio promedio de las viviendas?
2. ¿Cómo varian los precios entre municipios?
3. ¿Existe relacion entre habitaciones y precio?
4. ¿Qué características aparecen con mayor frecuencia en las viviendas de precios altos?
5. ¿Qué diferencias observables existen entre canales informales y fuentes estructuradas?
6. ¿Se pueden agrupar las viviendas en diferentes tipos según sus características?
7. ¿Cómo cambia el precio equivalente al convertir USD, CUP y EUR con tasas informal y formal?
8. ¿Qué influencia ha tenido la migracion en la oferta, la demanda y los precios de las viviendas entre 2020 y 2026?
9. ¿Qué parte del precio puede explicarse con los datos disponibles y qué queda sin cobertura?

## Objetivo del proyecto

Analizar el mercado inmobiliario de La Habana a partir de anuncios reales, distinguiendo datos verificados, datos derivados y datos no disponibles. El proyecto debe ser reproducible y defendible academically.

## Estructura y propósito

- `data/`, `outputs/` y los CSV derivados son datos locales y deben permanecer fuera de Git cuando correspondan.
- `data/raw/` contiene respaldos originales y no debe modificarse.
- Los scripts deben conservar la trazabilidad entre fuente, anuncio, limpieza e integración.
- No modificar ni sobrescribir archivos CSV originales.
- No reorganizar carpetas sin una razón técnica documentada.

## Reglas de trabajo

1. Preferir cambios justificados y verificables.
2. Ejecutar pruebas disponibles antes de afirmar que algo funciona.
3. No inventar valores para campos ausentes.
4. Distinguir entre:
   - dato inexistente,
   - dato no extraído,
   - dato que requiere revisión manual.
5. Documentar las limitaciones de los datos y del scraping.
6. No exponer credenciales, tokens ni datos privados.
7. No ejecutar operaciones destructivas ni migraciones innecesarias.
8. No borrar resultados previos sin autorización.
9. No rehacer tareas ya completadas si la evidencia muestra que funcionan.

## Datos y auditoría

- `anuncios_revolico_procesados.csv`, `viviendas_revolico_candidatas.csv`, `anuncios_revolico_revisar.csv` y `anuncios_revolico_excluidos.csv` deben conservarse como están.
- `texto_tarjeta` no debe usarse como feature individual sin reextracción controlada.
- Los precios en CUP de Revolico deben marcarse como sospechosos hasta validación.
- `municipio` y `habitaciones` tienen baja cobertura; no se deben imputar sin documentar.
- Los anuncios no equivalen a transacciones reales.

## Fuentes

- Revolico: fuente principal, pero bloqueada para scraping automático; usar HTML guardado.
- Cubisima: fuente complementaria accesible.
- HogarEnCuba: fuente estructurada con cobertura parcial de superficie.
- Facebook/Telegram: solo evidencia manual o encuesta anónima; no scraping automático.

## Código

- Los scripts deben fallar de forma clara ante datos faltantes.
- Los cambios en selectores o patrones deben documentarse.
- Los resultados derivados deben guardarse en `outputs/`.
- Los scripts de limpieza deben ser no destructivos.
- Las conversiones de moneda deben registrar la tasa usada y su fecha.

## Commits

- Usar mensajes técnicos y claros.
- No subir datos grandes, outputs ni archivos temporales.
- No subir guías personales ni material irrelevante.
- No reescribir el historial sin una razón clara.

## Entrevistas

- Anonimizar respuestas como E1, E2, ...
- No publicar datos personales.
- Cruzar respuestas con tablas y gráficos, pero sin atribuir causalidad directa.

## Calidad académica

- Distinguir asociación de causalidad.
- Reportar ausencias, outliers y sesgos.
- Incluir limitaciones en el informe final.
- No presentar análisis que no pueda justificarse con los datos disponibles.

## Decisiones vigentes (20/10/2026)

Reglas ya aplicadas que deben mantenerse en cualquier tarea nueva:

- **Alcance**: el maestro excluye 6 anuncios no residenciales y 28 fuera de alcance (13 fuera de La Habana, 15 no vivienda). Las exclusiones se auditan por URL en `revision_manual/exclusiones_alcance.csv`; 14 anuncios de alcance dudoso se conservan y se listan en `revision_manual/alcance_dudoso.csv`.
- **Municipios**: solo se homologan los 15 municipios de La Habana (`ubicaciones.py`). Las zonas o barrios de Cubisima no se imputan como municipio.
- **Precios**: `precio_original`/`moneda` conservan lo publicado; `precio_analisis`/`moneda_analisis` usan la reextracción manual verificada y excluyen lo sospechoso. No se corrige el campo publicado.
- **EUR**: se conserva en euros porque la descripción del vendedor lo dice literalmente, aunque el JSON-LD de HogarEnCuba indique USD; el conflicto se documenta y no se interpreta (n=3).
- **CUP**: queda marcado como sospechoso y fuera de toda conversión.
- **CUC**: solo se convierte con la paridad nominal declarada 1 CUC = 1 USD, nunca como tasa de mercado.
- **Superficie (m²)**: fuera del análisis; ninguna fuente la publica de forma sistemática.
- **Gráficos y tablas**: excluir monedas con n<5, combinaciones fuente-moneda con n<10 y grupos con n<5, anotando las exclusiones en la propia figura.
- **Segmentación**: terciles (33/66), no cuartiles. **Clustering**: k=3 por moneda, con etiquetas económico/medio/alto ordenadas por mediana.
- **Sesgo de disponibilidad**: 153 anuncios de Revolico ya no son accesibles; se marcan con su ventana de despublicación y no se descartan.
- **Tiempo**: sin serie temporal de precios; no se atribuye la evolución ni el efecto de la migración de forma cuantitativa.
- **Informe final**: no se redacta sin autorización expresa del usuario.