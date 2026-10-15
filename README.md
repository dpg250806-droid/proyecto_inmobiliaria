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
- `2026-10-15` - Subida a GitHub del commit `f5100ad` con el scraper hibrido, auditoria, limpieza no destructiva y documentacion. Los archivos derivados pesados (`data/`, `outputs/`, CSV reparado) se mantienen solo localmente.

## Limitaciones conocidas

- Las paginas HTML originales estan ignoradas por Git; por tanto, el repositorio contiene derivados, pero no el material fuente descargado.
- El precio se extrae del titulo con una expresion regular simple y puede capturar numeros que no son precios.
- `municipio` y `habitaciones` tienen ausencia alta porque solo se extraen del titulo.
- `texto_tarjeta` no es un texto individual confiable para analisis.
- `datos_revolico_json.csv` no es una fuente de viviendas exclusiva; contiene anuncios de productos diversos.
- No se han verificado las paginas individuales de anuncios para confirmar baños, metros cuadrados, planta, garaje o fechas.
- No se ha integrado la fuente Cubisima ni se ha modificado `analisis_inmobiliario.py`.
- No se han hecho commits ni cambios remotos en esta etapa.

## Datos aun no verificados

- Correspondencia exacta entre cada anuncio y su pagina individual.
- Validez real de precios atipicos (1 USD, 52.849.429, etc.) contra el texto original.
- Cobertura completa y representatividad del muestreo de 8 paginas.
- Disponibilidad y calidad de variables adicionales (baños, m2, planta, fecha, garaje, balcon, terraza).
- Analisis estadistico, visualizaciones, modelos predictivos o conclusiones sustantivas del mercado.

No se han modificado scripts existentes ni archivos CSV originales durante esta etapa de auditoria.