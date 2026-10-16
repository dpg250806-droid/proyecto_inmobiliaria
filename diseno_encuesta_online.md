# Formulario online de encuesta para WhatsApp

Diseño tentativo para aplicar el cuestionario por mensaje directo o grupos de compraventa, con respuestas anónimas.

## Herramienta recomendada
Google Forms o Jotform, configurado con opcion `sin iniciar sesion`.

## Encuesta

1. Relacion con la vivienda (marcar): propietario, heredero, inquilino, comprador potencial, otra (especificar).

2. Municipio de la vivienda con mayor conocimiento (marcar): todos los municipios de La Habana, otra (especificar).

3. ¿Como han evolucionado los precios desde 2020? (texto libre).

4. Factores que determinan el precio (marcar varias): ubicación, tamaño, estado constructivo, moneda, canal de venta, otra.

5. Influencia del USD, EUR y tasas oficiales/informales (texto libre).

6. ¿Los precios publicados reflejan el valor real? Si/No y justificacion.

7. Influencia de la migracion en la oferta y demanda (texto libre).

8. Crisis, tasas y migracion: cual influyo mas y por que (texto libre).

9. Factores que reducen el precio inicial o dificultan la venta (texto libre).

10. Canales mas efectivos e información que debe incluir el anuncio (texto libre).

## Campos finales
- Desea dejar nombre o identificador? Si/No.
- Comentario adicional opcional.

## Configuracion sugerida
- Respuestas ilimitadas por persona (o limite por navegador si se quiere control).
- No pedir correo electronico ni telefono.
- Usar seccion inicial con consentimiento informado.
- Notificar por correo al propietario de la encuesta.
- Exportar a CSV a medida que aumentan las respuestas.

## Esquema para integrar respuestas
Columnas recomendadas:
- id_respuesta
- fecha_utc
- anonimo
- relacion_vivienda
- municipio
- precio_evolution
- factores_marcados
- influencia_monedas
- refleja_valor_real
- migracion_influencia
- principal_factor
- factores_reduccion_precio
- canales_ideales
- comentario

## Buena practica
- No capturar datos personales identificables.
- Separar agregados de citas textuales.
- Cruce con la mediana de precios y con preguntas del analisis tabular.

## Envio
- WhatsApp directo o estados.
- Telegram en grupos de compraventa.
- Facebook en grupos relacionados (sin automatizar, solo publicacion manual del link).
PY