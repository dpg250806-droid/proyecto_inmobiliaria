# Bitácora de cambios técnicos

Registro cronológico de modificaciones del repositorio. Las horas corresponden al
reloj local del entorno de trabajo (UTC−04:00). No sustituye la evidencia fuente
ni registra ejecuciones en línea que no se hayan realizado.

## 2026-10-21

### 16:24:06 — Auditoría reproducible y salidas analíticas seguras

- Maestro verificado en modo local: `outputs/integracion/dataset_maestro_20261020_234716.csv`
  (1.516 filas: Revolico 748, Cubisima 585 y HogarEnCuba 183; sin IDs ni URLs duplicados).
- Los resúmenes de precios, municipios, habitaciones, canales y segmentación ahora
  aplican los umbrales de publicación definidos en `AGENTS.md`: moneda n>=5,
  fuente-moneda n>=10 y grupo n>=5, con exclusiones indicadas donde corresponde.
- Los gráficos y reportes de comparativos, segmentación, clustering, visualizaciones
  y preguntas reciben rutas fechadas que no reutilizan archivos existentes.
- `control_calidad.py` compila scripts en memoria, revisa el inventario SHA-256
  sin distinguir mayúsculas/minúsculas y reconoce los dos fixtures históricos
  retirados que siguen listados en el inventario.
- Se agregaron pruebas offline para umbrales, filtro municipal y rutas sin
  sobrescritura; se fijaron las dependencias existentes en `requirements.txt`.
- README, diccionario, fuentes, matriz y documentación preliminar sincronizados
  con el maestro verificado. Los outputs y CSV locales no se reemplazaron.
- Validación: 74 pruebas unitarias correctas; 52 archivos Python compilan en
  memoria; control de calidad correcto; 8+5+2+1 imágenes generadas en una carpeta
  temporal e inspeccionadas como PNG legibles.
- No se ejecutaron scrapers ni solicitudes de red. No se hizo commit ni push.

### 20:31:45 — Estado de outputs y prueba de scrapers

- Revisión de 577 archivos locales en `outputs/`: los reportes analíticos más
  recientes remiten al maestro `dataset_maestro_20261020_234716.csv` y a las
  conversiones basadas en ese mismo maestro. Los archivos fechados anteriores
  se conservan como histórico; no se actualizaron los datos originales.
- Los 61 PNG existentes se abrieron/verificaron como imágenes válidas. La última
  generación de gráficas es del 20/10/2026 por la noche, posterior a la creación
  del maestro vigente. El corte de datos sigue siendo 19/10/2026: “vigente”
  significa último conjunto disponible, no datos de mercado de hoy.
- Pruebas en carpeta temporal: Cubisima HTTP 200, 24 anuncios en la primera de
  25 páginas; HogarEnCuba procesó 13 anuncios de la primera de 10 páginas y sus
  13 detalles sin fallos (marcó correctamente la descarga parcial); Revolico
  en línea respondió HTTP 403, mientras el modo local procesó 111 anuncios de
  una página HTML guardada.
- Se corrigió el mensaje de estado de Cubisima para mostrar por separado el
  total detectado y las páginas limitadas por `--max-pages`.
- Suite: 74 pruebas correctas. No se ejecutó el rastreo completo ni se guardó
  ninguno de esos resultados temporales en `outputs/` o en los CSV originales.
