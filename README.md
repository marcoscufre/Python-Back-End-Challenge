# Document Processing Gateway - Coding Challenge

## Contexto
Este microservicio orquesta el procesamiento de documentos a través de un pipeline de proveedores externos (simulados). El sistema maneja el ciclo de vida de cada "Job" de forma asíncrona utilizando Redis Streams para el Event Streaming.

## Arquitectura
1.  **API REST (Django + DRF):** Recibe los documentos y gestiona el estado de los procesos.
2.  **Event Streaming (Redis Streams):** Actúa como el broker de eventos, garantizando persistencia y permitiendo grupos de consumidores.
3.  **Orquestador (Consumer):** Un proceso independiente que consume eventos, ejecuta las etapas del pipeline y publica actualizaciones.
4.  **Mocks de Proveedores:** Implementaciones simuladas de Extracción (Fast/Slow), Análisis y Enriquecimiento con latencia real controlada.

## Justificación de Tecnologías
-   **Django (Async capabilities):** Se utilizó Django por su robustez y su soporte para operaciones asíncronas y comandos de gestión de larga duración.
-   **Redis Streams:** Elegido sobre RabbitMQ o Kafka por su simplicidad de despliegue y soporte nativo para **Consumer Groups** y **Acknowledgment**, cumpliendo con los requisitos de persistencia y escalabilidad sin añadir complejidad excesiva.
-   **Resiliencia:** Se implementó una estrategia de **Retry con Exponential Backoff** en el orquestador para manejar fallas temporales en los proveedores externos.

## Eventos Implementados
-   `job.created`: Cuando se recibe el documento.
-   `job.stage_started`: Inicio de una etapa (Extracción, Análisis, etc).
-   `job.stage_completed`: Fin exitoso de una etapa con resultado parcial.
-   `job.completed`: Pipeline finalizado exitosamente.
-   `job.failed`: Error en alguna etapa (después de reintentos).
-   `job.cancelled`: Cancelación manual por el usuario.

## Cómo ejecutar el proyecto

### Requisitos
-   Docker y Docker Compose

### Pasos
1.  Construir y levantar los contenedores:
    ```bash
    docker-compose up --build
    ```
2.  Ejecutar migraciones (dentro del contenedor web):
    ```bash
    docker-compose exec web python manage.py migrate
    ```

### Endpoints Principales
-   `POST /api/jobs/`: Enviar documento. 
    Payload: `{"nombre": "Doc", "tipo": "PDF", "contenido": "...", "pipeline_config": ["extraction", "analysis"]}`
-   `GET /api/jobs/{id}/`: Consultar estado y resultados.
-   `POST /api/jobs/{id}/cancel/`: Cancelar proceso en curso.
-   `GET /api/jobs/?status=processing`: Listar jobs filtrados por estado.

## Ejecución de Tests
```bash
python -m pytest
```
