import pytest
import redis
import json
import time
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient
from processing.models import Job, JobStatus
from processing.management.commands.run_event_consumer import Command as OrchestratorCommand

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def redis_client():
    client = redis.from_url(settings.REDIS_URL)
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis is not available")
    return client

@pytest.mark.django_db
def test_full_pipeline_integration(api_client, redis_client):
    """
    Test de integración de punta a punta:
    1. Crea un job vía API (valida DB + Publicación Redis)
    2. Lee el evento de Redis (valida Streaming)
    3. Ejecuta el orquestador manualmente (valida Pipeline + Providers)
    4. Verifica el estado final en DB
    """
    # Limpiar stream antes de empezar
    stream_name = 'job_events'
    redis_client.delete(stream_name)
    
    # 1. Crear Job
    url = reverse('job-list')
    payload = {
        "nombre": "Doc Integracion",
        "tipo": "Integration",
        "contenido": "Contenido para test de integración",
        "pipeline_config": [
            {"stage": "extraction", "config": {"variant": "fast"}},
            "analysis"
        ]
    }
    
    response = api_client.post(url, payload, format='json')
    assert response.status_code == 201
    job_id = response.data['job_id']
    
    # 2. Verificar que el evento llegó a Redis
    # Esperamos un momento para asegurar persistencia (aunque Redis es rápido)
    events = redis_client.xread({stream_name: '0'}, count=10)
    assert len(events) > 0
    
    # Buscar el evento job.created
    found_created = False
    for stream, msgs in events:
        for msg_id, data in msgs:
            if data[b'event_type'].decode('utf-8') == 'job.created':
                found_created = True
                break
    assert found_created, "El evento job.created no se encontró en Redis"

    # 3. Ejecutar el orquestador para este job (simulando el worker)
    orchestrator = OrchestratorCommand()
    # No corremos handle() porque es un loop infinito, corremos la lógica directamente
    orchestrator.run_pipeline(str(job_id))
    
    # 4. Verificar estado final
    job = Job.objects.get(id=job_id)
    assert job.status == JobStatus.COMPLETED
    assert 'extraction' in job.results
    assert 'analysis' in job.results
    
    # 5. Verificar que se emitieron los eventos de finalización
    events_after = redis_client.xread({stream_name: '0'}, count=50)
    event_types = [msg[1][b'event_type'].decode('utf-8') for stream, msgs in events_after for msg in msgs]
    
    assert 'job.stage_started' in event_types
    assert 'job.stage_completed' in event_types
    assert 'job.completed' in event_types
