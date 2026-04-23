import pytest
from unittest.mock import patch, MagicMock
from processing.models import Job, JobStatus
from processing.management.commands.run_event_consumer import Command as ConsumerCommand

@pytest.mark.django_db
class TestOrchestrator:
    def test_run_pipeline_success(self):
        job = Job.objects.create(
            nombre="Doc", tipo="TXT", contenido="Hello",
            pipeline_config=["extraction", "analysis"]
        )
        command = ConsumerCommand()
        
        # Mocks para providers
        mock_extraction = MagicMock()
        mock_extraction.process.return_value = "extracted text"
        mock_analysis = MagicMock()
        mock_analysis.process.return_value = {"tags": ["test"]}
        
        def get_provider_mock(stage, config):
            if stage == "extraction": return mock_extraction
            if stage == "analysis": return mock_analysis
            return None

        with patch('processing.management.commands.run_event_consumer.get_provider', side_effect=get_provider_mock), \
             patch('processing.management.commands.run_event_consumer.publisher.publish') as mock_publish:
            
            command.run_pipeline(str(job.id))
            
            job.refresh_from_db()
            assert job.status == JobStatus.COMPLETED
            assert job.results['extraction'] == "extracted text"
            assert job.results['analysis'] == {"tags": ["test"]}
            
            # Verificar eventos (creado, started x2, completed x2, job.completed)
            # Notar que job.created ya fue enviado por la vista, aquí probamos los del pipeline
            assert mock_publish.call_count >= 5 

    def test_consumer_handles_xautoclaim_failure(self):
        command = ConsumerCommand()
        command.redis_client = MagicMock()
        # Forzar error en xautoclaim
        command.redis_client.xautoclaim.side_effect = Exception("Redis error")
        # Forzar salida del loop en la siguiente instrucción
        command.redis_client.xreadgroup.side_effect = KeyboardInterrupt()
        
        with patch.object(command.stdout, 'write') as mock_stdout:
            try:
                command.handle()
            except KeyboardInterrupt:
                pass
            
            # Verificar que se escribió el error en stdout/stderr
            args, _ = mock_stdout.call_args_list[1] # La primera es "Orchestrator started..."
            assert "XAUTOCLAIM failed: Redis error" in args[0]
