# Informe preliminar del mercado inmobiliario cubano

Fecha de datos: 18 de octubre de 2026.
Base integrada: 1566 anuncios (`outputs/integracion/dataset_maestro_20261018_141637.csv`).

## Fuentes
- Revolico: 780 anuncios desde HTML local; el acceso online sigue bloqueado por Cloudflare.
- Cubisima: 598 anuncios de la captura online; la copia local procesada (`viviendas_cubisima.csv`) conserva 625 filas.
- HogarEnCuba: 188 fichas de captura integral (10 de 10 páginas, 0 fallidas).

## Variables con mejor cobertura
- Cubisima: ubicacion, habitaciones, banos, precio y fecha (100%); no publica superficie.
- HogarEnCuba: ubicacion, habitaciones, banos y precio (100%, con 2 banos, 2 precios y 1 m2 verificados manualmente); m2 en 9/188; fecha en 88% pero relativa ("hace 2 años").
- Revolico: volumen alto, pero municipio 37%, habitaciones 9%, banos 0% y fecha 0%.

## Resultados observados
- Precio mediano por fuente y moneda: HogarEnCuba USD 61500; Cubisima CUC 25000; Revolico USD 25000. Solo USD se compara entre fuentes.
- Los 546 anuncios CUC de Cubisima se publicaron entre el 17/10/2023 y el 12/10/2026, todos posteriores a la desmonetizacion del CUC; se valoran en USD con paridad declarada 1 CUC = 1 USD (529 convertidos, 17 precios excluidos: 6 con valor 1 y 11 revisados manualmente), no como tasa de mercado.
- La asociacion entre precio y caracteristicas es positiva en todas las fuentes con datos: habitaciones (rho de Spearman 0.58 a 0.75) y banos (0.63 a 0.73). La superficie solo se puede estudiar en HogarEnCuba y con n reducido (9).
- El clustering (k-means, k=3, por moneda) separa en CUC (Cubisima) un grupo economico (307 anuncios, mediana 14000), uno medio (185, 55000) y uno alto (37, 250000); en USD (HogarEnCuba) uno economico (104, 40000), uno medio (70, 120000) y uno alto (12, 750000).
- La divergencia entre tasas informal y formal cambia el valor equivalente del mismo precio en EUR; en CUC no aplica por ser conversion nominal.
- La segmentacion por cuartiles muestra una separacion clara entre viviendas economicas, medias y altas dentro de cada moneda.

## Comparacion de canales
- Revolico: alto volumen, baja cobertura de metadatos y sin fecha de publicacion.
- Cubisima: mejor cobertura estructurada (banos, zona, fecha) y unico registro masivo de precio en CUC.
- HogarEnCuba: mayor precio mediano y unico con superficie, pero menor volumen y fechas relativas.

## Limitaciones
- Revolico bloqueado para scraping automatico; se usa HTML guardado.
- Los anuncios no son transacciones cerradas.
- m2 disponible en muy pocos casos (9 de 1566) y no se imputa.
- Los 5 anuncios en CUP de Revolico se marcan como sospechosos y quedan fuera de conversion.
- Los 59 precios inferiores a 100 se revisaron uno a uno contra la descripcion del anuncio (`revisar_descripciones_precios_bajos.py`): 13 tenian el precio del campo publicado erroneo (la descripcion indicaba montos entre 6000 y 90000 USD), 4 eran productos, 1 permuta, 1 local comercial, 4 anuncios retirados y 14 sin precio en la descripcion. Los 37 quedan marcados como sospechosos con su veredicto en `veredicto_revision`; la evidencia esta en `revision_manual/precios_bajos.csv` y en `outputs/validacion/revision_descripciones_*.md`.
- La misma revision detecto un error de lectura con decimales por coma ("7,5 USD" se habia leido como 75) y municipios del sitio inconsistentes con el propio texto en al menos 2 anuncios; ambos quedan documentados como limitacion.
- Las tasas online se obtienen por registro manual por bloqueo anti-bot (ultimo registro: 15/10/2026).
- La migracion no puede atribuirse porcentualmente con anuncios transversales.

## Siguiente paso
Triangular los resultados con las entrevistas (2 respuestas hasta el 15/10/2026) y ampliar la cobertura de superficie solo cuando exista en la fuente.
