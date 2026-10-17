# AGENTS.md

## Alcance

Este archivo define reglas para trabajar en el proyecto inmobiliario basado en anuncios de Revolico y fuentes complementarias.

## Objetivo del proyecto

Analizar el mercado inmobiliario de La Habana a partir de anuncios reales, distinguiendo datos verificados, datos derivados y datos no disponibles. El proyecto debe ser reproducible y defendible academically.

## Estructura y propósito

- `data/`, `outputs/` y los CSV derivados son datos locales y deben permanecer fuera de Git cuando correspondan.
- `data/raw/` contiene respaldos originales y no debe modificarse.
- Los scripts deben conservar la trazabilidad entre fuente, anuncio, limpieza e integración.
- No modificar ni sobrescribir archivos CSV originales.
- No reorganizar carpetas sin una razón técnica documentada.

## Reglas de trabajo

1. Preferir cambios pequeños, justificados y verificables.
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

- Usar commits pequeños y con mensaje técnico.
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
PY