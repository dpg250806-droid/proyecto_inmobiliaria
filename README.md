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
- `analisis_inmobiliario.py`: script didactico con datos de ejemplo. No analiza el dataset real y puede sobrescribir `viviendas.csv`, `viviendas_limpias.csv` y `anuncio.json`.
- `auditoria_revolico.py`: auditoria exclusivamente de lectura. Genera un informe en `outputs/auditoria/`.
- `limpiar_revolico.py`: limpieza no destructiva. Genera un dataset derivado y un resumen en `outputs/limpieza/`.
- Scripts exploratorios: `inspeccionar_revolico.py`, `buscar_datos_ocultos_revolico.py`, `diagnostico_json_revolico.py`, `extraer_datos_revolico.py`.

## Auditoria

Ejecutar:

```bash
python auditoria_revolico.py
```

El script solo lee los CSV y escribe un reporte nuevo en `outputs/auditoria/`. No modifica los CSV de entrada.

## Bitacora de desarrollo (cronologica)

Esta seccion resume el trabajo realizado y la fecha/hora de cada bloque, para servir como mapa del proceso.

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

## Limitaciones conocidas

- Las paginas HTML originales estan ignoradas por Git; por tanto, el repositorio contiene derivados, pero no el material fuente descargado.
- El precio se extrae del titulo con una expresion regular simple y puede capturar numeros que no son precios.
- `municipio` y `habitaciones` tienen ausencia alta porque solo se extraen del titulo.
- `texto_tarjeta` no es un texto individual confiable para analisis.
- `datos_revolico_json.csv` no es una fuente de viviendas exclusiva; contiene anuncios de productos diversos.
- No se han verificado las paginas individuales de anuncios para confirmar ba├▒os, metros cuadrados, planta, garaje o fechas.
- No se ha integrado la fuente Cubisima ni se ha modificado `analisis_inmobiliario.py`.
- No se han hecho commits ni cambios remotos en esta etapa.

## Datos aun no verificados

- Correspondencia exacta entre cada anuncio y su pagina individual.
- Validez real de precios atipicos (1 USD, 52.849.429, etc.) contra el texto original.
- Cobertura completa y representatividad del muestreo de 8 paginas.
- Disponibilidad y calidad de variables adicionales (ba├▒os, m2, planta, fecha, garaje, balcon, terraza).
- Analisis estadistico, visualizaciones, modelos predictivos o conclusiones sustantivas del mercado.

No se han modificado scripts existentes ni archivos CSV originales durante esta etapa de auditoria.

## Fuentes integradas

- Revolico: anuncios base, mas volumen y precios en USD/CUP; municipio y habitaciones con baja cobertura.
- Cubisima: mas variables estructuradas, especialmente banos y zona.
- HogarEnCuba: prueba formal con fichas que incluyen superficie y banos en algunos casos.

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
- Superficie disponible solo en parte de HogarEnCuba.
- Moneda CUP requiere depuracion manual.
- Los anuncios no equivalen a transacciones cerradas.


## Cuestionario anonimo

Enlace: https://forms.gle/Lk3vod7cQuGHZwub9
