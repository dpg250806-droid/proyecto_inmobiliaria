# Formulario online de encuesta para WhatsApp

**Estado:** aplicado el 15–19/10/2026; se recogen **10 respuestas** (E01–E10) en `data/entrevistas/` y se procesan con `procesar_entrevistas.py`. Este documento conserva el diseño original por si hay que ampliar la muestra.

Diseño para aplicar el cuestionario por mensaje directo o en grupos de compraventa, con respuestas anónimas. El instrumento en versión texto está en [`cuestionario_entrevistas.md`](cuestionario_entrevistas.md).

## Herramienta recomendada

Google Forms o Jotform, configurado con la opción `sin iniciar sesión`.

## Encuesta

1. Relación con la vivienda (marcar): propietario, heredero, inquilino, comprador potencial, otra (especificar).
2. Municipio de la vivienda con mayor conocimiento (marcar): los 15 municipios de La Habana, otra (especificar).
3. ¿Cómo han evolucionado los precios desde 2020? (texto libre).
4. Factores que determinan el precio (marcar varias): ubicación, tamaño, estado constructivo, moneda, canal de venta, otra.
5. Influencia del USD, el EUR y las tasas oficiales e informales (texto libre).
6. ¿Los precios publicados reflejan el valor real? Sí/No y justificación.
7. Influencia de la migración en la oferta y la demanda (texto libre).
8. Crisis, tasas y migración: ¿cuál influyó más y por qué? (texto libre).
9. Factores que reducen el precio inicial o dificultan la venta (texto libre).
10. Canales más efectivos e información que debe incluir el anuncio (texto libre).

## Campos finales

- ¿Desea dejar nombre o identificador? Sí/No.
- Comentario adicional opcional.

## Configuración sugerida

- Respuestas ilimitadas por persona (o límite por navegador si se quiere control).
- No pedir correo electrónico ni teléfono.
- Usar una sección inicial de consentimiento informado.
- Notificar por correo al propietario de la encuesta.
- Exportar a CSV a medida que aumentan las respuestas.

## Esquema para integrar respuestas

Columnas de la exportación original (`data/entrevistas/`):

- `id_respuesta`, `fecha_utc`, `anonimo`,
- `relacion_vivienda`, `municipio`,
- `precio_evolution`, `factores_marcados`, `influencia_monedas`, `refleja_valor_real`,
- `migracion_influencia`, `principal_factor`, `factores_reduccion_precio`,
- `canales_ideales`, `comentario`.

`procesar_entrevistas.py` anonimiza (E01…E0N), descarta columnas identificables y deriva los códigos C1–C7 antes de escribir en `outputs/entrevistas/`.

## Buenas prácticas

- No capturar datos personales identificables.
- Separar agregados de citas textuales.
- Cruzar con la mediana de precios y con las preguntas del análisis tabular, **sin atribuir causalidad**.

## Envío

- WhatsApp directo o estados.
- Telegram en grupos de compraventa.
- Facebook en grupos relacionados (sin automatizar: solo publicación manual del enlace).
