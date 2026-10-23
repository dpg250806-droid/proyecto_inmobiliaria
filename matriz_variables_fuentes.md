# Matriz de variables por fuente

**Corte de datos:** 19/10/2026 · **Cifras verificadas:** 21/10/2026. Maestro vigente: 1.516 anuncios (Revolico 748, Cubisima 585, HogarEnCuba 183).

Dos coberturas se reportan por separado y no deben mezclarse:

- **Publicado**: lo que la fuente ofrece en su ficha o tarjeta (mide el canal).
- **De análisis**: lo que se obtiene después de leer texto, página individual y enlace (mide el trabajo de recuperación).

## Fuentes integradas

| Fuente | Rol | Precio publicado | Precio de análisis | Moneda | Municipio/zona publicada | Municipio de análisis | Habitaciones publicadas | Habitaciones de análisis | Baños publicados | Baños de análisis | Superficie m² | Fecha | Características | Acceso |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Revolico | Informal, alto volumen | 709/748 (94,8 %) | 691/748 (92,4 %) | USD, CUP | 286/748 (38,2 %) | 650/748 (86,9 %) | 69/748 (9,2 %) | 526/748 (70,3 %) | 0/748 | 284/748 (38,0 %) | no | 595/748 (79,5 %) | no | listado bloqueado; ficha individual consultada en la captura |
| Cubisima | Estructurada, único bloque masivo en CUC | 535/585 (91,5 %) | 530/585 (90,6 %) | CUC; 50 sin moneda publicada en el maestro | 585/585 (zonas y barrios) | 98/585 (16,8 %) | 585/585 | 585/585 | 585/585 | 585/585 | no | 585/585 | 6 campos declarados | última ejecución confirmada: 27 páginas HTTP 200; no revalidada en esta auditoría |
| HogarEnCuba | Estructurada, precio más alto | 183/183 | 183/183 | USD, EUR | 183/183 | 183/183 | 183/183 | 183/183 | 183/183 | 183/183 | 9/183 (4,9 %) | 162/183 (88,5 %) | no | último snapshot local: 10 páginas, sin fallos; no revalidado en esta auditoría |

## Fuentes candidatas (no integradas)

| Fuente | Rol posible | Precio | Moneda | Municipio/zona | Habitaciones | Baños | Superficie m² | Fecha | Características | Acceso |
|---|---|---|---|---|---|---|---|---|---|---|
| Casas Oasis | estructurada | por verificar | USD/CUP | por verificar | probable | probable | probable | probable | mayor detalle | accesible públicamente |
| Busca Tu Choza | clasificado local | por verificar | por verificar | por verificar | probable | probable | por verificar | por verificar | media | accesible por verificación |
| HousesCuba | turistico | no aplica | — | — | — | — | — | — | — | no priorizada |

## Lectura de la matriz

- **Revolico** es la fuente más escasa en metadato publicado y la más abundante en metadato recuperable: la diferencia entre 38,2 % y 86,9 % en ubicación, y entre 9,2 % y 70,3 % en habitaciones, es trabajo de lectura de la ficha individual, no cobertura de la fuente.
- **Cubisima** es la única que publica las seis características auxiliares; su "ubicación" mezcla niveles geográficos y por eso no se convierte en municipio salvo coincidencia exacta (98 de 585).
- **HogarEnCuba** es la única con superficie, pero en menos del 5 % de las fichas: **la superficie no alcanza cobertura suficiente para usarse como variable explicativa** y queda fuera del análisis.
- La **fecha** es la única variable donde las tres fuentes son incomparables: HogarEnCuba publica fechas relativas y Revolico no publica fecha (la que se usa es la de última actualización de la página).
- Ninguna fuente publica **agencia** de forma sistemática: el campo `agencia_observada` recoge la evidencia textual cuando aparece, sin inferir lo que no se declara.
