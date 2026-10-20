# Matriz de variables por fuente

**Corte de datos:** 19/10/2026. Las cifras son sobre el maestro vigente (1.532 anuncios: Revolico 755, Cubisima 594, HogarEnCuba 183).

Dos coberturas se reportan por separado y no deben mezclarse:

- **Publicado**: lo que la fuente ofrece en su ficha o tarjeta (mide el canal).
- **De análisis**: lo que se obtiene después de leer texto, página individual y enlace (mide el trabajo de recuperación).

## Fuentes integradas

| Fuente | Rol | Precio publicado | Precio de análisis | Moneda | Municipio/zona publicada | Municipio de análisis | Habitaciones publicadas | Habitaciones de análisis | Baños publicados | Baños de análisis | Superficie m² | Fecha | Características | Acceso |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Revolico | Informal, alto volumen | 714/755 (94,6 %) | 691/755 (91,5 %) | USD, CUP | 287/755 (38,0 %) | 657/755 (87,0 %) | 69/755 (9,1 %) | 528/755 (69,9 %) | 0/755 | 285/755 (37,7 %) | no | 602/755 (79,7 %) | no | listado bloqueado; ficha individual responde |
| Cubisima | Estructurada, único bloque masivo en CUC | 543/594 (91,4 %) | 536/594 (90,2 %) | CUC, USD, EUR | 594/594 (zonas y barrios) | 100/594 (16,8 %) | 594/594 | 594/594 | 594/594 | 594/594 | no | 594/594 | 6 campos declarados | accesible con `requests` |
| HogarEnCuba | Estructurada, precio más alto | 183/183 | 183/183 | USD, EUR | 183/183 | 183/183 | 183/183 | 183/183 | 183/183 | 183/183 | 9/183 (4,9 %) | 162/183 (88,5 %) | no | accesible con carga filtrada |

## Fuentes candidatas (no integradas)

| Fuente | Rol posible | Precio | Moneda | Municipio/zona | Habitaciones | Baños | Superficie m² | Fecha | Características | Acceso |
|---|---|---|---|---|---|---|---|---|---|---|
| Casas Oasis | estructurada | por verificar | USD/CUP | por verificar | probable | probable | probable | probable | mayor detalle | accesible públicamente |
| Busca Tu Choza | clasificado local | por verificar | por verificar | por verificar | probable | probable | por verificar | por verificar | media | accesible por verificación |
| HousesCuba | turistico | no aplica | — | — | — | — | — | — | — | no priorizada |

## Lectura de la matriz

- **Revolico** es la fuente más escasa en metadato publicado y la más abundante en metadato recuperable: la diferencia entre 38,0 % y 87,0 % en ubicación, y entre 9,1 % y 69,9 % en habitaciones, es trabajo de lectura de la ficha individual, no cobertura de la fuente.
- **Cubisima** es la única que publica las seis características auxiliares; su "ubicación" mezcla niveles geográficos y por eso no se convierte en municipio salvo coincidencia exacta (100 de 594).
- **HogarEnCuba** es la única con superficie, pero en menos del 5 % de las fichas: **la superficie no alcanza cobertura suficiente para usarse como variable explicativa** y queda fuera del análisis.
- La **fecha** es la única variable donde las tres fuentes son incomparables: HogarEnCuba publica fechas relativas y Revolico no publica fecha (la que se usa es la de última actualización de la página).
- Ninguna fuente publica **agencia** de forma sistemática: el campo `agencia_observada` recoge la evidencia textual cuando aparece, sin inferir lo que no se declara.
