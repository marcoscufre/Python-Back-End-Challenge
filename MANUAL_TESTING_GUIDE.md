# Guía de Testing Manual - Document Processing Gateway

Esta guía detalla cómo probar todos los flujos del sistema utilizando Postman o comandos `curl`.

## 1. Configuración Inicial (Postman)
- **Base URL:** `http://localhost:8000/api`
- **Headers:** `Content-Type: application/json`

---

## 2. Endpoints de Jobs (POST)

### A. Crear Job - Flujo Exitoso
**POST** `/jobs/`
```json
{
    "nombre": "Documento Legal",
    "tipo": "PDF",
    "contenido": "Contenido crudo para procesar...",
    "pipeline_config": [
        {"stage": "extraction", "config": {"variant": "fast"}},
        "analysis",
        "enrichment"
    ]
}
```

### B. Crear Job - Error: Más de 3 etapas
**POST** `/jobs/`
```json
{
    "nombre": "Doc Fallido",
    "tipo": "TXT",
    "contenido": "...",
    "pipeline_config": ["extraction", "analysis", "enrichment", "analysis"]
}
```
*Respuesta esperada: `400 Bad Request` con mensaje de error.*

### C. Cancelar un Job
**POST** `/jobs/{id}/cancel/`
- No requiere body.
- *Nota: Úsalo mientras el job está en estado `processing` para ver al orquestador detenerse.*

---

## 3. Endpoints de Consulta (GET)

### A. Listar todos los Jobs
**GET** `/jobs/`

### B. Listar con Filtro de Estado
**GET** `/jobs/?status=completed`
- Otros estados: `pending`, `processing`, `failed`, `cancelled`.

### C. Detalle de Job (Ver resultados del Pipeline)
**GET** `/jobs/{id}/`
*Aquí podrás ver el campo `results` con los datos generados por cada etapa (extraction, analysis, etc.).*

---

## 4. Testeo con `curl` (Terminal)

### Crear un job rápidamente:
```bash
curl -X POST http://localhost:8000/api/jobs/ \
     -H "Content-Type: application/json" \
     -d '{"nombre":"Test Curl","tipo":"TXT","contenido":"Hola mundo","pipeline_config":["extraction","analysis"]}'
```

### Ver el listado de jobs procesados (para ver el trabajo del consumidor):
```bash
curl -X GET "http://localhost:8000/api/jobs/?status=completed"
```

### Consultar un job específico y sus metadatos:
```bash
# Reemplaza {id} con el UUID obtenido al crear el job
curl -X GET http://localhost:8000/api/jobs/{id}/
```

---

## 5. Monitoreo de Consumidores (Logs)
Para ver cómo los consumidores (Orquestador y Downstream) reaccionan en tiempo real a tus peticiones de Postman:

```bash
# Ver al orquestador ejecutando el pipeline
docker-compose logs -f event_consumer

# Ver al consumidor downstream logueando eventos
docker-compose logs -f downstream_consumer
```
