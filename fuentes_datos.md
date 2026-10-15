# Fuentes cubanas de viviendas: estado de verificacion

Actualizado: 2026-10-15.

## 1. Revolico (fuente principal)

- URL base usada: `https://www.revolico.com/search?category=inmobiliaria&subcategory=inmobiliaria-casas&province=la-habana`
- Estado online: **bloqueado por Cloudflare/anti-bot** para scraping automatico (HTTP 403; Playwright y Selenium tambien recibieron la pagina "Un momento...").
- Solucion operativa: guardar manualmente las paginas HTML y procesarlas localmente.
- Datos actuales: 780 anuncios unicos extraidos de 8 paginas HTML locales.
- Fortaleza: gran volumen de anuncios y precios en USD/CUP.
- Limitacion: municipio y habitaciones con alta ausencia; los detalles fisicos aparecen rara vez en el titulo.

## 2. Cubisima (fuente adicional verificada)

- URL base usada: `https://www.cubisima.com/casas/anuncios/la-habana/`
- Estado online: **accesible** con `requests`.
- Ultima ejecucion: 25 paginas y 598 anuncios unicos.
- Campos disponibles observados: tipo, zona, habitaciones, baños, precio, moneda, fecha, garaje, piscina, terraza, patio, balcon, jardin.
- Fortaleza: mas variables estructuradas que Revolico.
- Limitacion: datos descargados online en esta etapa; deben revisarse estandarizacion y posibles duplicados entre fuentes.

## 3. Casas Oasis (fuente candidata verificada por busqueda web)

- URL observada: `https://casasoasis.com/es/venta/viviendas`
- Estado: pagina accesible en la busqueda web.
- Ejemplo observado en La Habana: casas con habitaciones, banos, fotos y fechas.
- Fortaleza potencial: datos bastante estructurados.
- Limitacion: aun no se ha implementado scraper ni validado su estructura completa.

## 4. HogarEnCuba (fuente candidata verificada por busqueda web)

- URL observada: `https://hogarencuba.com/ventas/la-habana`
- Estado: pagina accesible en la busqueda web.
- Ejemplo observado: 199 opciones en La Habana, precio promedio 132.628 US$, cuartos y baños en el titulo.
- Fortaleza potencial: clasificacion por municipio y tipo de propiedad.
- Limitacion: aun no se ha implementado scraper.

## 5. Busca Tu Choza (fuente candidata verificada por busqueda web)

- URL observada: `https://buscatuchoza.com/`
- Estado: pagina accesible en la busqueda web.
- Ejemplo observado: habitaciones, baños y metros cuadrados en los anuncios.
- Fortaleza potencial: detalle mas completo en algunos anuncios.
- Limitacion: aun no se ha implementado scraper.

## 6. HousesCuba (no priorizada)

- URL observada: `https://www.housescuba.com/`
- Parece orientada a alojamientos turisticos, no a venta inmobiliaria general. No priorizada para esta etapa.

## Conclusion para el proyecto

Para la investigacion academica actual se recomienda:
1. Mantener Revolico como fuente principal (volumen alto).
2. Usar Cubisima como fuente complementaria (mas variables).
3. Dejar Casas Oasis, HogarEnCuba y Busca Tu Choza como fuentes futuras para ampliar y validar conclusiones.

Antes de mezclar fuentes, habra que estandarizar moneda, ubicacion, tipo de vivienda y fechas.