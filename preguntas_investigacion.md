# Preguntas de investigación

**Proyecto:** mercado inmobiliario de La Habana a partir de anuncios de Revolico, Cubisima y HogarEnCuba, con entrevistas anónimas como evidencia cualitativa.
**Corte de datos:** 19/10/2026. Las respuestas tabuladas se regeneran con `python analisis_preguntas.py` en `outputs/preguntas/`.

## Pregunta principal

¿Qué características observables y condiciones contextuales (precio, moneda, municipio/zona, habitaciones, baños, superficie, estado, características auxiliares, canal de venta y fecha) se asocian con el precio publicado de viviendas en La Habana?

## Preguntas secundarias

1. ¿Cuál es el precio mediano y promedio por fuente, moneda y municipio/zona?
2. ¿Cómo varían los precios entre municipios/zonas?
3. ¿Cómo se relacionan habitaciones y baños con el precio?
4. ¿Qué características aparecen con mayor frecuencia en las viviendas de precio más alto?
5. ¿Qué diferencias observables existen entre canales informales (clasificados individuales) y canales formales o estructurados (inmobiliarias/plataformas especializadas)?
6. ¿Se pueden agrupar las viviendas en perfiles homogéneos?
7. ¿Qué diferencias existen entre el precio inicial y el precio equivalente convertido con tasa informal frente a formal?
8. ¿Qué evidencia documental y testimonial sugiere presión de venta asociada a la migración en 2020–2026?
9. ¿Qué parte del precio puede explicarse con los datos disponibles y qué queda sin cobertura?

## Alcance operativo y advertencias metodológicas

- **Asociación, no causalidad.** Ninguna respuesta se redacta como efecto causal; la migración no se atribuye porcentualmente porque no hay serie temporal de precios.
- **Comparación dentro de la misma moneda.** Los importes en USD, CUC y EUR no se comparan entre sí; el CUC se convierte solo con la paridad nominal declarada.
- **Municipios y zonas no son equivalentes.** Solo se comparan municipios homologados de La Habana; las zonas de Cubisima se reportan aparte.
- **Umbrales de publicación.** Monedas con n<5, combinaciones fuente-moneda con n<10 y grupos con n<5 no se interpretan; sus exclusiones se anotan en cada figura.
- **Dato ausente ≠ dato inventado.** Lo que no existe, lo que no se extrajo y lo pendiente de revisión manual se distinguen y se reportan por separado.
