# Cuestionario de entrevistas (proyecto inmobiliario)

**Estado:** instrumento aplicado el 15–19/10/2026 a **10 personas** (E01–E10). La versión web equivalente está en [`diseno_encuesta_online.md`](diseno_encuesta_online.md).

Escala sugerida: 10 a 15 personas, organizadas por perfil:
- propietario que ha intentado vender,
- comprador potencial o familiar vinculado a una venta,
- agente o intermediario,
- observador que siguió el proceso (familiar o abogado).

Registrar por entrevista: municipio, año de la decisión, tipo de vivienda, moneda usada y cualquier dato demográfico útil.

## Preguntas

1. ¿Cuál es su relación con la vivienda (propietario, heredero, inquilino, comprador potencial u otra) y en qué municipio se encuentra la vivienda con la que tiene mayor conocimiento?
2. En su opinión, ¿cómo han evolucionado los precios de las viviendas en Cuba desde 2020 hasta la actualidad? ¿A qué atribuye esos cambios?
3. ¿Cuáles considera que son los principales factores que determinan el precio de una vivienda en Cuba (ubicación, tamaño, estado constructivo, moneda u otros)?
4. ¿Qué influencia cree que tienen el USD, el EUR y las tasas de cambio oficiales e informales en la fijación de los precios de las viviendas?
5. ¿Considera que los precios publicados en los anuncios inmobiliarios reflejan el valor real de las viviendas? ¿Por qué?
6. ¿Qué influencia considera que ha tenido la migración en la oferta, la demanda y los precios de las viviendas en Cuba durante el período estudiado?
7. Entre la crisis económica, las variaciones de las tasas de cambio y la migración, ¿cuál considera que ha influido más en el mercado inmobiliario cubano? ¿Por qué?
8. ¿Qué factores podrían llevar a una persona a reducir el precio solicitado por su vivienda o dificultar su venta?
9. ¿Qué canales considera más efectivos para ofertar viviendas en Cuba y qué información debería incluir un anuncio para generar confianza?

## Reglas de aplicación

- **Anonimato en la captura**: la exportación no debe incluir correo, nombre ni teléfono. `procesar_entrevistas.py` descarta cualquier columna identificable antes de escribir la salida.
- **Identificadores**: cada respuesta se etiqueta `E01`…`E0N` en el orden de entrada y no se conserva ningún metadato personal.
- **Citas**: se conservan fragmentos literales en `A1_cita` (primeros 220 caracteres) para poder reabrir cada caso en el informe.
- **Muestra no probabilística**: los resultados describen percepciones y mecanismos; no estiman prevalencias ni causalidad.

## Codificación útil

- relación con la vivienda,
- causa de cambio de precio,
- moneda usada,
- tasa mencionada,
- impacto de la migración,
- canal de venta,
- confianza en el anuncio.

Los códigos automáticos C1–C7 (detalle en `data_dictionary.md`) se calculan sobre el texto completo con búsqueda por subcadena, sin tildes y en minúsculas:

| Código | Criterio | Frecuencia (n=10) |
|---|---|---:|
| `C1_necesidad_economica` | dinero, necesidad, urgencia o miseria | 9 |
| `C2_migracion` | migra*, travesía, Nicaragua, salir del país, irse del país | 10 |
| `C3_moneda_tasa` | USD, CUP, tasa(s), moneda, divisa, dólar, euro, MLC | 8 |
| `C4_canal_venta` | Telegram, WhatsApp, Facebook o grupo | 4 |
| `C5_precio_alto` | caro, carísimo, regalo o valor | 7 |
| `C6_caracteristicas` | m2, metro, baño(s) o piscina | 2 |
| `C7_municipio` | cualquier municipio de La Habana en el texto | 10 |

Son heurísticas de frecuencia para organizar el discurso, no sustituyen la lectura manual.

## Uso posterior

Cruzar las respuestas con:
- la mediana por fuente y moneda,
- la diferencia entre precio informal y formal (tasa),
- la cobertura de superficie y de baños,
- la presencia de características en las viviendas de precio alto.

El cruce se describe como **coincidencia de direcciones**, nunca como estimación de efecto.
