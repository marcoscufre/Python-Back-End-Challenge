Efectivamente, al ser una API REST sin interfaz gráfica, Postman es la herramienta ideal para testear el flujo completo.

  Aquí tienes los pasos y los payloads exactos para probar todas las mejoras que implementamos:

  1. Crear un Job (POST)
  Envía una petición POST a http://localhost:8000/api/jobs/ con el siguiente JSON:

    1 {
    2     "nombre": "Documento de Prueba",
    3     "tipo": "PDF",
    4     "contenido": "Texto largo que simula el contenido de un documento",
    5     "pipeline_config": [
    6         {"stage": "extraction", "config": {"variant": "slow"}},
    7         "analysis",
    8         "enrichment"
    9     ]
   10 }
   * Qué observar: Recibirás un 201 Created con un job_id. Si intentas apagar Redis y enviar esto, verás el error 503 que implementamos para evitar
     jobs huérfanos.

  2. Consultar el Estado (GET)
  Usa el job_id recibido para consultar http://localhost:8000/api/jobs/{id}/.
   * Qué observar: Verás cómo el status cambia de pending a processing y finalmente a completed. En el campo results verás cómo se van llenando las
     etapas a medida que el orquestador las procesa.

  3. Listar con Filtros (GET)
  Puedes listar todos los trabajos filtrando por estado:
  http://localhost:8000/api/jobs/?status=completed

  4. Cancelar un Job (POST)
  Si el job está en una etapa lenta (como el slow extractor de 2 segundos), puedes intentar cancelarlo:
  http://localhost:8000/api/jobs/{id}/cancel/ (sin cuerpo)
   * Qué observar: El orquestador detectará la cancelación antes de pasar a la siguiente etapa y se detendrá.

  ---

  ¿Cómo ver los Consumidores en acción?

  Como ahora tienes dos consumidores corriendo en Docker (el orquestador y el de logs), puedes ver "la magia" en tu terminal:

   1. Ver el Orquestador procesando:

   1     docker-compose logs -f event_consumer
   2. Ver el nuevo Consumidor Downstream (el que creamos hoy):

   1     docker-compose logs -f downstream_consumer
      En este verás pasar todos los eventos: job.created, job.stage_started, job.completed, etc. Esto demuestra que el sistema de streaming funciona
  correctamente para múltiples servicios.

  Alternativa rápida (cURL)
  Si no quieres abrir Postman, puedes usar este comando en tu terminal:

   1 curl -X POST http://localhost:8000/api/jobs/ -H "Content-Type: application/json" -d
     "{\"nombre\":\"Test\",\"tipo\":\"TXT\",\"contenido\":\"Hola\",\"pipeline_config\":[\"extraction\"]}"