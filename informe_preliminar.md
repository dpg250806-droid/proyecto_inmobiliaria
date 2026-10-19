# Informe preliminar del mercado inmobiliario cubano

Fecha de datos: 18 de octubre de 2026.
Base integrada: 1566 anuncios (`outputs/integracion/dataset_maestro_20261018_194612.csv`).

## Fuentes
- Revolico: 780 anuncios desde HTML local; el acceso online sigue bloqueado por Cloudflare. La pagina individual de cada anuncio si responde, y de ahi se extrajeron municipio, fecha y el texto completo (`extraer_metadatos_revolico.py`); habitaciones y banos se leen de ese texto (`extraer_detalle_anuncios_revolico.py`).
- Cubisima: 598 anuncios de la captura online; la copia local procesada (`viviendas_cubisima.csv`) conserva 625 filas.
- HogarEnCuba: 188 fichas de captura integral (10 de 10 páginas, 0 fallidas).

## Variables con mejor cobertura
- Cubisima: ubicacion, habitaciones, banos, precio y fecha (100%); no publica superficie.
- HogarEnCuba: ubicacion, habitaciones, banos y precio (100%, con 2 banos, 2 precios y 1 m2 verificados manualmente); m2 en 9/188; fecha en 88% pero relativa ("hace 2 años").
- Revolico: volumen alto. El campo publicado solo cubre municipio 37%, habitaciones 9%, banos 0% y fecha 0%, pero el texto del anuncio (descripcion, titulo y enlace) eleva las habitaciones de analisis a 532/780 (68%) y los banos a 289/780 (37%); el municipio de analisis queda en 677/780 (87%) y la fecha en 622 anuncios (`updatedOnByUser`: es la fecha de ultima actualizacion que el sitio muestra como "hace X dias", no la de creacion ni la de venta). 158 anuncios ya no estan accesibles (83 despublicados, 75 borrados).

## Resultados observados
- Precio mediano por fuente y moneda (`precio_analisis`): HogarEnCuba USD 61500 (n=186); Revolico USD 25000 (n=697); Cubisima CUC 25000 (n=529); Cubisima USD 35000 (n=4, reextracciones). Solo USD es comparable entre fuentes.
- Los 546 anuncios CUC de Cubisima se publicaron entre el 17/10/2023 y el 12/10/2026, todos posteriores a la desmonetizacion del CUC; se valoran en USD con paridad declarada 1 CUC = 1 USD (529 convertidos, 17 precios excluidos: 6 con valor 1 y 11 revisados manualmente), no como tasa de mercado.
- La asociacion entre precio y caracteristicas es positiva en las tres fuentes. Habitaciones (rho de Spearman): Cubisima CUC 0.61, HogarEnCuba USD 0.61, Revolico USD 0.59. Banos: HogarEnCuba 0.73, Cubisima 0.68, Revolico 0.55. En Revolico la mediana por habitaciones sube de 10500 (1 habitacion, n=48) a 45000 (3, n=159) y 70000 (4, n=55); por banos, de 22500 (1, n=82) a 80000 (3, n=47).
- El clustering (k-means, k=3, por moneda) separa en CUC (Cubisima) un grupo economico (307 anuncios, mediana 14000), uno medio (185, 55000) y uno alto (37, 250000); en USD, con las tres fuentes integradas por primera vez (438 observaciones), uno economico (249, 30000), uno medio (165, 90000) y uno alto (24, 600000).
- La divergencia entre tasas informal y formal cambia el valor equivalente del mismo precio en EUR; en CUC no aplica por ser conversion nominal.
- La segmentacion por cuartiles muestra una separacion clara entre viviendas economicas, medias y altas dentro de cada moneda.
- Con el municipio verificado en la pagina del anuncio, la comparacion por municipio ya es posible dentro de Revolico USD: Playa 50000 (n=137), Plaza 45000 (n=85), Centro Habana y Diez de Octubre con volumen suficiente; sigue sin ser comparable con las zonas de Cubisima (Siboney, Miramar, Vedado), que no son municipios homologos.
- Las 622 fechas de pagina de Revolico van del 17/05/2025 al 18/10/2026, pero 619 de ellas son de agosto a octubre de 2026: miden frescura del anuncio, no momento de la operacion.

## Comparacion de canales
- Revolico: alto volumen; con la pagina del anuncio y su texto recupera municipio (87%), habitaciones (68%), banos (37%) y fecha (622 anuncios). 158 anuncios ya no estan accesibles.
- Cubisima: mejor cobertura estructurada (banos, zona, fecha) y unico registro masivo de precio en CUC.
- HogarEnCuba: mayor precio mediano y unico que publica superficie (aunque solo en 9/188), pero menor volumen y fechas relativas.

## Limitaciones
- El listado de Revolico esta bloqueado para scraping automatico; se usa HTML guardado. La extraccion de metadatos consulta la pagina individual de cada anuncio con espera y reintentos, y registra su estado.
- Los anuncios no son transacciones cerradas.
- La fecha de Revolico es `updatedOnByUser` (fecha de actualizacion mostrada como "hace X dias"); no confirma fecha de creacion ni de venta, y no se mezcla con `fecha_publicacion` de las otras fuentes.
- Sesion de disponibilidad: 158 de 780 anuncios de Revolico ya no estan accesibles (83 despublicados, 75 borrados). No se descartan: quedan marcados con `fecha_ultima_disponibilidad` (2026-09-29, fecha del listado guardado donde aun aparecian), `ventana_despublicacion` (2026-09-29 a 2026-10-18, la consulta que devolvio el error) y `justificacion_disponibilidad`. La pagina borrada no conserva fecha, asi que la desaparicion solo puede acotarse a ese intervalo; esto introduce sesgo de disponibilidad.
- Habitaciones y banos de Revolico se leen del texto del anuncio con cobertura parcial (532 y 289 de 780). El techo lo fija el propio texto: los 158 anuncios inaccesibles no tienen descripcion, y otros anuncios publicados simplemente no mencionan la cantidad. No se imputa nada; los 83 casos en los que titulo y descripcion dan cantidades distintas quedan marcados en `conflicto_detalle` sin resolverse.
- Municipio de Cubisima en la tabla por zona son zonas (Siboney, Miramar, Vedado), no municipios homologos con los de Revolico y HogarEnCuba.
- m2 excluido del analisis: Revolico y Cubisima lo publican en 0% y HogarEnCuba en 9/188 (~5%); ninguna fuente llega al 100%, por lo que no se usa como variable explicativa. Se conserva en el maestro como traza y su ausencia queda documentada como hallazgo comparativo: el clasificado informal no ofrece superficie.
- Los 5 anuncios en CUP de Revolico se marcan como sospechosos y quedan fuera de conversion.
- Los 59 precios inferiores a 100 se revisaron uno a uno contra la descripcion del anuncio (`revisar_descripciones_precios_bajos.py`): 13 tenian el precio del campo publicado erroneo (la descripcion indicaba montos entre 6000 y 90000 USD), 4 eran productos, 1 permuta, 1 local comercial, 4 anuncios retirados y 14 sin precio en la descripcion. Los 37 quedan marcados como sospechosos con su veredicto en `veredicto_revision`; la evidencia esta en `revision_manual/precios_bajos.csv` y en `outputs/validacion/revision_descripciones_*.md`.
- Los 13 precios erroneos se reincorporaron por reextraccion documentada: 12 tienen precio verificado en la descripcion o en el titulo del anuncio, registrado en `precio_reextraido`/`moneda_reextraida`/`evidencia_precio`; el campo publicado no se corrige. El analisis usa `precio_analisis` (reextraccion primero, luego campo publicado no sospechoso); 1 anuncio sigue excluido por no tener precio verificable. De ellos, 4 de Cubisima pasan de CUC a USD (18000, 20000, 50000 y 90000) y 8 de Revolico suman a USD.
- La misma revision detecto un error de lectura con decimales por coma ("7,5 USD" se habia leido como 75) y municipios del sitio inconsistentes con el propio texto en al menos 2 anuncios; ambos quedan documentados como limitacion.
- Las tasas online se obtienen por registro manual por bloqueo anti-bot (ultimo registro: 15/10/2026).
- La migracion no puede atribuirse porcentualmente con anuncios transversales.

## Siguiente paso
Triangular los resultados con las entrevistas (2 respuestas hasta el 15/10/2026). La superficie solo se retomara si alguna fuente la publica de forma completa.
