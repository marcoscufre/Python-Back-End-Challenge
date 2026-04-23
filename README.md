# Document Processing Gateway - Coding Challenge

## Contexto
Este microservicio orquesta el procesamiento de documentos a través de un pipeline de proveedores externos (simulados). El sistema maneja el ciclo de vida de cada "Job" de forma asíncrona utilizando **Redis Streams** para el Event Streaming, garantizando que ninguna tarea se pierda incluso ante caídas de los servicios.

## Arquitectura y Componentes
El sistema se compone de cuatro piezas fundamentales que interactúan de forma desacoplada:

1.  **API REST (Django + DRF):** Punto de entrada que valida y persiste los Jobs en base de datos. Publica el evento inicial en Redis.
2.  **Event Streaming (Redis Streams):** Broker persistente que utiliza **Consumer Groups**. Esto permite que múltiples servicios (Orquestador y Downstream) consuman los mismos eventos de forma independiente y con confirmación explícita (ACK).
3.  **Orquestador (Orchestrator):** Proceso worker que consume `job.created`, ejecuta el pipeline secuencial, gestiona reintentos y actualiza el estado del Job.
4.  **Consumidor de Logs (Downstream):** Segundo servicio independiente que demuestra la escalabilidad del streaming, consumiendo todos los eventos del sistema para auditoría y logging.

## Mecanismos de Resiliencia (Critical Points)
-   **Garantía de Entrega (At-least-once):** Tanto el Orquestador como el Downstream recuperan mensajes pendientes (`PEL`) al iniciar y utilizan `XAUTOCLAIM` para rescatar mensajes que quedaron "huérfanos" si otro consumidor del grupo cae.
-   **Consistencia de Datos:** La API prioriza la base de datos como fuente de verdad. Si la publicación en Redis falla con errores ambiguos (timeouts), el registro se mantiene para evitar inconsistencias, y el sistema responde con el estado real de la operación.
-   **Retry con Backoff:** El orquestador implementa reintentos exponenciales (1s, 2s, 4s) para mitigar fallos transitorios en proveedores externos.
-   **Validación Temprana:** Se validan formatos y límites (máx 3 etapas) en la API para evitar inyectar basura en el pipeline.

## Eventos del Sistema
-   `job.created`: Disparo inicial del pipeline.
-   `job.stage_started` / `job.stage_completed`: Tracking granular del progreso.
-   `job.completed` / `job.failed`: Estados finales del ciclo de vida.
-   `job.cancelled`: Señal para que el orquestador detenga la ejecución entre etapas.

## Cómo ejecutar el proyecto

### Requisitos
-   Docker y Docker Compose

### Pasos
1.  **Levantar infraestructura:**
    ```bash
    docker-compose up --build
    ```
2.  **Inicializar Base de Datos:**
    En una nueva terminal, ejecuta:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

### Guía de Pruebas Rápidas
Se ha incluido un archivo detallado `MANUAL_TESTING_GUIDE.md` con payloads de Postman y comandos `curl`.

#### Crear un Job:
```bash
curl -X POST http://localhost:8000/api/jobs/ \
     -H "Content-Type: application/json" \
     -d '{"nombre":"Test","tipo":"PDF","contenido":"...","pipeline_config":["extraction","analysis"]}'
```

## Monitoreo
Puedes ver a los diferentes servicios trabajando en paralelo:
```bash
# Ver el pipeline en ejecución
docker-compose logs -f event_consumer

# Ver el flujo de eventos downstream
docker-compose logs -f downstream_consumer
```

## Ejecución de Tests
La suite incluye unit tests y un test de integración **End-to-End** real:
```bash
python -m pytest
```
