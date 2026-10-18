# Informe preliminar del mercado inmobiliario cubano

Fecha de datos: 18 de octubre de 2026.
Base integrada: 1566 anuncios (`outputs/integracion/dataset_maestro_20261018_003336.csv`).

## Fuentes
- Revolico: 780 anuncios desde HTML local; el acceso online sigue bloqueado por Cloudflare.
- Cubisima: 598 anuncios de la captura online; la copia local procesada (`viviendas_cubisima.csv`) conserva 625 filas.
- HogarEnCuba: 188 fichas de captura integral (10 de 10 páginas, 0 fallidas).

## Variables con mejor cobertura
- Cubisima: ubicacion, habitaciones, banos, precio y fecha (100%); no publica superficie.
- HogarEnCuba: ubicacion, habitaciones, banos y precio (100%, con 2 baños y 3 precios verificados manualmente); m2 en 9/188; fecha en 88% pero relativa ("hace 2 años").
- Revolico: volumen alto, pero municipio 37%, habitaciones 9%, banos 0% y fecha 0%.

## Resultados observados
- Precio mediano por fuente y moneda: HogarEnCuba USD 61500; Cubisima CUC 25000; Revolico USD 23500. Solo USD se compara entre fuentes.
- Los 546 anuncios CUC de Cubisima se publicaron entre el 17/10/2023 y el 12/10/2026, todos posteriores a la desmonetizacion del CUC; se valoran en USD con paridad declarada 1 CUC = 1 USD (540 convertidos, 6 precios sospechosos excluidos), no como tasa de mercado.
- La asociacion entre precio y caracteristicas es positiva en todas las fuentes con datos: habitaciones (rho de Spearman 0.58 a 0.75) y banos (0.63 a 0.73). La superficie solo se puede estudiar en HogarEnCuba y con n reducido (9).
- El clustering de Cubisima (k-means, k=3) separa un grupo economico (358 anuncios, mediana 15000), uno medio (152, 60000) y uno alto (30, 260000).
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
- 123 precios se marcan como sospechosos por umbral alto; quedan 59 precios inferiores a 100 pendientes de criterio de exclusion documentado.
- Las tasas online se obtienen por registro manual por bloqueo anti-bot (ultimo registro: 15/10/2026).
- La migracion no puede atribuirse porcentualmente con anuncios transversales.

## Siguiente paso
Triangular los resultados con las entrevistas (2 respuestas hasta el 15/10/2026) y ampliar la cobertura de superficie solo cuando exista en la fuente.
