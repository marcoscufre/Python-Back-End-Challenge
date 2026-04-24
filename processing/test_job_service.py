import pytest
from django.core.exceptions import ValidationError
from processing.models import Job
from processing.services.job_service import JobService
from unittest.mock import patch

@pytest.mark.django_db
class TestJobService:
    def test_validate_input_valid(self):
        nombre, tipo, contenido = "Job", "Type", "Content"
        config = ['extraction']
        clean_data = JobService.validate_input(nombre, tipo, contenido, config)
        
        assert clean_data['nombre'] == nombre
        assert clean_data['pipeline_config'] == [{'stage': 'extraction', 'config': {}}]

    def test_validate_input_invalid_name(self):
        with pytest.raises(ValidationError, match="Invalid name"):
            JobService.validate_input("", "type", "content", [])

    def test_validate_input_name_too_long(self):
        with pytest.raises(ValidationError, match="Invalid name"):
            JobService.validate_input("a" * 256, "type", "content", [])

    def test_validate_input_invalid_pipeline_list(self):
        with pytest.raises(ValidationError, match="must be a list"):
            JobService.validate_input("Name", "Type", "Content", "not a list")

    @patch('processing.services.events.publisher.publish')
    def test_create_job_success(self, mock_publish):
        mock_publish.return_value = True
        
        job, success = JobService.create_job(
            nombre="Test Job",
            tipo="test",
            contenido="content",
            pipeline_config=['extraction']
        )
        
        assert isinstance(job, Job)
        assert job.nombre == "Test Job"
        assert job.pipeline_config == [{'stage': 'extraction', 'config': {}}]
        assert success is True
        assert mock_publish.called

    def test_get_job_exists(self):
        job = Job.objects.create(
            nombre="Existing",
            tipo="test",
            contenido="content",
            pipeline_config=[]
        )
        fetched = JobService.get_job(str(job.id))
        assert fetched == job

    def test_get_job_not_found(self):
        assert JobService.get_job("00000000-0000-0000-0000-000000000000") is None
