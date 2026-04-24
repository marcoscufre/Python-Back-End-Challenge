# Document Processing Gateway

## Descripcion
Este proyecto implementa un microservicio backend para procesar documentos a traves de un pipeline de proveedores externos simulados. El sistema recibe documentos, crea un `Job`, publica eventos en Redis Streams, ejecuta las etapas configuradas del pipeline y deja el estado y los resultados disponibles para consulta.

La solucion cubre:

- API REST para crear, listar, consultar y cancelar jobs.
- Event streaming con Redis Streams.
- Orquestador asincrono por consumer group.
- Consumidor downstream separado para logging y auditoria.
- Bonus gRPC para `CreateJob` y `GetJob`.
- Tests unitarios, de servicio, integracion y gRPC.

## Stack Tecnologico
- Python 3.10+
- Django
- Django REST Framework
- PostgreSQL
- Redis Streams
- gRPC / Protocol Buffers
- Docker Compose
- Pytest

## Arquitectura
Los componentes principales son:

1. `web`
   API REST levantada con Django + DRF y servida con Uvicorn.
2. `db`
   PostgreSQL para persistir jobs, estados y resultados.
3. `redis`
   Broker de eventos usando Redis Streams.
4. `event_consumer`
   Worker que consume `job.created`, ejecuta el pipeline y publica eventos del progreso.
5. `downstream_consumer`
   Consumidor independiente que lee el stream y loguea los eventos procesados.
6. `grpc_server`
   Interfaz gRPC alternativa para crear jobs y consultar jobs reutilizando la misma capa de servicio que REST.

## Flujo General
1. El cliente crea un job por REST o gRPC.
2. El servicio valida la entrada y persiste el `Job` en base de datos con estado `pending`.
3. Se publica el evento `job.created` en Redis Streams.
4. El `event_consumer` toma ese evento y cambia el job a `processing`.
5. El worker ejecuta secuencialmente las etapas de `pipeline_config`.
6. En cada etapa publica `job.stage_started` y `job.stage_completed`.
7. Si todo sale bien, el job termina en `completed`.
8. Si una etapa falla luego de reintentos, el job termina en `failed`.
9. Si el usuario cancela el job, pasa a `cancelled` y el worker detiene la ejecucion entre etapas.

## Estados del Job
Los estados posibles son:

- `pending`
- `processing`
- `completed`
- `failed`
- `cancelled`

## Eventos Publicados
El stream principal es `job_events`.

Eventos emitidos:

- `job.created`
- `job.stage_started`
- `job.stage_completed`
- `job.completed`
- `job.failed`
- `job.cancelled`

Cada evento incluye:

- `job_id`
- `timestamp`
- `event_type`
- `payload`

## Resiliencia Implementada
- Redis Streams con persistencia de mensajes.
- Consumer groups con `XACK`.
- Recuperacion de mensajes pendientes del propio consumidor.
- Reclamo de mensajes huerfanos con `XAUTOCLAIM`.
- Retry con backoff exponencial para proveedores.
- Manejo de falla ambigua de publicacion: el job se mantiene en DB y el cliente recibe error coherente.

## Estructura Principal
```text
backend/
  settings.py
  urls.py
  asgi.py
  wsgi.py

processing/
  models.py
  serializers.py
  views.py
  urls.py
  services/
    events.py
    job_service.py
    providers.py
  management/commands/
    run_event_consumer.py
    run_downstream_consumer.py
    run_grpc_server.py
  proto/
    jobs.proto
    jobs_pb2.py
    jobs_pb2_grpc.py
  tests.py
  test_job_service.py
  test_orchestrator.py
  test_integration_e2e.py
  test_grpc.py
```

## Requisitos para correr el proyecto
- Docker Desktop o Docker Engine
- Docker Compose

Opcional para correr fuera de Docker:
- Python 3.10+
- pip

## Como levantar el proyecto con Docker
Desde la raiz del repo:

```bash
docker compose up --build
```

Esto levanta:

- PostgreSQL en el contenedor `db`
- Redis en el contenedor `redis`
- API REST en `http://localhost:8000`
- gRPC en `localhost:50051`
- Worker orquestador en `event_consumer`
- Worker downstream en `downstream_consumer`

## Migraciones
Una vez levantados los contenedores, en otra terminal corre:

```bash
docker compose exec web python manage.py migrate
```

Si queres crear un superusuario:

```bash
docker compose exec web python manage.py createsuperuser
```

## Endpoints REST
Base URL:

```text
http://localhost:8000/api/
```

Operaciones principales:

- `POST /api/jobs/`
- `GET /api/jobs/`
- `GET /api/jobs/{job_id}/`
- `POST /api/jobs/{job_id}/cancel/`

### Crear Job
```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Documento Legal",
    "tipo": "PDF",
    "contenido": "Contenido crudo para procesar...",
    "pipeline_config": [
      {"stage": "extraction", "config": {"variant": "fast"}},
      "analysis",
      "enrichment"
    ]
  }'
```

Respuesta esperada:
```json
{
  "job_id": "uuid-del-job"
}
```

### Listar Jobs
```bash
curl http://localhost:8000/api/jobs/
```

### Filtrar por estado
```bash
curl "http://localhost:8000/api/jobs/?status=processing"
```

### Consultar un Job
```bash
curl http://localhost:8000/api/jobs/<JOB_ID>/
```

### Cancelar un Job
```bash
curl -X POST http://localhost:8000/api/jobs/<JOB_ID>/cancel/
```

## Interfaz gRPC
El servidor gRPC expone dos operaciones:

- `CreateJob`
- `GetJob`

Puerto:

```text
localhost:50051
```

Contrato:

- Archivo `.proto`: [processing/proto/jobs.proto](/C:/Users/marcos/Desktop/python backend challenge/processing/proto/jobs.proto:1)

### Probar con grpcurl
Crear job:

```bash
grpcurl -plaintext -import-path . -proto processing/proto/jobs.proto \
  -d '{
    "nombre": "Job gRPC",
    "tipo": "TEXT",
    "contenido": "contenido desde grpc",
    "pipeline_config": [
      {"stage": "extraction", "variant": "slow"},
      {"stage": "analysis"}
    ]
  }' \
  localhost:50051 jobs.JobService/CreateJob
```

Consultar job:

```bash
grpcurl -plaintext -import-path . -proto processing/proto/jobs.proto \
  -d '{"job_id":"<JOB_ID>"}' \
  localhost:50051 jobs.JobService/GetJob
```

## Monitoreo y Logs
Ver logs del orquestador:

```bash
docker compose logs -f event_consumer
```

Ver logs del consumer downstream:

```bash
docker compose logs -f downstream_consumer
```

Ver logs del servidor gRPC:

```bash
docker compose logs -f grpc_server
```

Ver logs de la API:

```bash
docker compose logs -f web
```

## Como correr los tests
Si usas la venv local:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

Ejecutar solo una suite:

```bash
.\.venv\Scripts\python.exe -m pytest processing\test_grpc.py
.\.venv\Scripts\python.exe -m pytest processing\test_integration_e2e.py
```

## Que valida la suite
- `processing/tests.py`
  Valida la API REST.
- `processing/test_job_service.py`
  Valida la capa de servicio compartida.
- `processing/test_orchestrator.py`
  Valida la logica del orquestador y manejo de `XAUTOCLAIM`.
- `processing/test_integration_e2e.py`
  Valida el flujo end-to-end principal.
- `processing/test_grpc.py`
  Valida la interfaz gRPC.

## Como correr local sin Docker
1. Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

2. Configurar variables de entorno:

```text
DATABASE_URL=postgres://user:password@localhost:5432/processing_db
REDIS_URL=redis://localhost:6379/0
```

3. Ejecutar migraciones:

```bash
python manage.py migrate
```

4. Levantar API:

```bash
uvicorn backend.asgi:application --host 0.0.0.0 --port 8000 --reload
```

5. Levantar worker principal:

```bash
python manage.py run_event_consumer
```

6. Levantar downstream:

```bash
python manage.py run_downstream_consumer
```

7. Levantar gRPC:

```bash
python manage.py run_grpc_server
```