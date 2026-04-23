import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from .models import Job, JobStatus
from unittest.mock import patch

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestJobAPI:
    def test_create_job(self, api_client):
        url = reverse('job-list')
        data = {
            "nombre": "Test Doc",
            "tipo": "PDF",
            "contenido": "Contenido de prueba",
            "pipeline_config": ["extraction", "analysis"]
        }
        with patch('processing.services.events.publisher.publish') as mock_publish:
            response = api_client.post(url, data, format='json')
            assert response.status_code == 201
            assert "job_id" in response.data
            
            job = Job.objects.get(id=response.data['job_id'])
            assert job.status == JobStatus.PENDING
            mock_publish.assert_called_with('job.created', job.id, {
                'nombre': job.nombre,
                'tipo': job.tipo,
                'pipeline_config': job.pipeline_config
            })

    def test_list_jobs_filter(self, api_client):
        Job.objects.create(nombre="J1", tipo="T", contenido="C", pipeline_config=[], status=JobStatus.COMPLETED)
        Job.objects.create(nombre="J2", tipo="T", contenido="C", pipeline_config=[], status=JobStatus.PENDING)
        
        url = reverse('job-list')
        response = api_client.get(url, {'status': 'completed'})
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_cancel_job(self, api_client):
        job = Job.objects.create(nombre="J1", tipo="T", contenido="C", pipeline_config=[], status=JobStatus.PROCESSING)
        url = reverse('job-cancel', kwargs={'pk': job.id})
        
        with patch('processing.services.events.publisher.publish') as mock_publish:
            response = api_client.post(url)
            assert response.status_code == 200
            job.refresh_from_db()
            assert job.status == JobStatus.CANCELLED
            mock_publish.assert_called_with('job.cancelled', job.id)

    def test_cannot_cancel_finished_job(self, api_client):
        job = Job.objects.create(nombre="J1", tipo="T", contenido="C", pipeline_config=[], status=JobStatus.COMPLETED)
        url = reverse('job-cancel', kwargs={'pk': job.id})
        response = api_client.post(url)
        assert response.status_code == 400

    def test_cancel_job_redis_failure_warning(self, api_client):
        job = Job.objects.create(nombre="J1", tipo="T", contenido="C", pipeline_config=[], status=JobStatus.PROCESSING)
        url = reverse('job-cancel', kwargs={'pk': job.id})
        
        with patch('processing.services.events.publisher.publish', return_value=False):
            response = api_client.post(url)
            assert response.status_code == 200
            assert "warning" in response.data
            job.refresh_from_db()
            assert job.status == JobStatus.CANCELLED

    def test_create_job_invalid_pipeline_too_many_stages(self, api_client):
        url = reverse('job-list')
        data = {
            "nombre": "Test", "tipo": "PDF", "contenido": "...",
            "pipeline_config": ["extraction", "analysis", "enrichment", "extraction"] # 4 stages
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 400
        assert "more than 3 stages" in str(response.data['pipeline_config'])

    def test_create_job_invalid_pipeline_wrong_type(self, api_client):
        url = reverse('job-list')
        data = {
            "nombre": "Test", "tipo": "PDF", "contenido": "...",
            "pipeline_config": ["extraction", 123] # Invalid type
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == 400
        assert "Must be string or object" in str(response.data['pipeline_config'])
