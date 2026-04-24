import pytest
import grpc
from unittest.mock import MagicMock, patch
from processing.management.commands.run_grpc_server import JobServiceServicer
from processing.proto import jobs_pb2
from processing.models import Job
import json

@pytest.mark.django_db
class TestGRPCService:
    def test_create_job_grpc_integration(self):
        """Test that gRPC CreateJob correctly persists to DB and maps pipeline_config."""
        servicer = JobServiceServicer()
        request = jobs_pb2.CreateJobRequest(
            nombre="Integration Job",
            tipo="test",
            contenido="content",
            pipeline_config=[
                jobs_pb2.Stage(stage="extraction", variant="slow"),
                jobs_pb2.Stage(stage="analysis")
            ]
        )
        context = MagicMock()
        
        # Act
        response = servicer.CreateJob(request, context)
        
        # Assert
        assert response.job_id != ""
        
        # Verify in DB
        job = Job.objects.get(id=response.job_id)
        assert job.nombre == "Integration Job"
        expected_pipeline = [
            {'stage': 'extraction', 'config': {'variant': 'slow'}},
            {'stage': 'analysis', 'config': {}}
        ]
        assert job.pipeline_config == expected_pipeline

    def test_create_job_grpc_validation_failure(self):
        """Test that gRPC CreateJob calls context.abort with INVALID_ARGUMENT."""
        servicer = JobServiceServicer()
        request = jobs_pb2.CreateJobRequest(
            nombre="", # Invalid empty name
            tipo="test",
            contenido="content",
            pipeline_config=[]
        )
        context = MagicMock()
        context.abort.side_effect = Exception("Aborted")
        
        with pytest.raises(Exception, match="Aborted"):
            servicer.CreateJob(request, context)
        
        # Verificamos que se llamó a context.abort con INVALID_ARGUMENT
        context.abort.assert_called_once()
        args, _ = context.abort.call_args
        assert args[0] == grpc.StatusCode.INVALID_ARGUMENT
        assert "Invalid name" in str(args[1])

    def test_get_job_grpc_success(self):
        job = Job.objects.create(
            nombre="GRPC Get",
            tipo="test",
            contenido="content",
            pipeline_config=[{'stage': 'extraction', 'config': {}}]
        )
        
        servicer = JobServiceServicer()
        request = jobs_pb2.GetJobRequest(job_id=str(job.id))
        context = MagicMock()
        
        response = servicer.GetJob(request, context)
        
        assert response.job.id == str(job.id)
        assert response.job.nombre == "GRPC Get"

    def test_get_job_grpc_not_found(self):
        """Test that gRPC GetJob calls context.abort with NOT_FOUND."""
        servicer = JobServiceServicer()
        request = jobs_pb2.GetJobRequest(job_id="00000000-0000-0000-0000-000000000000")
        context = MagicMock()
        context.abort.side_effect = Exception("Aborted")
        
        with pytest.raises(Exception, match="Aborted"):
            servicer.GetJob(request, context)
        
        context.abort.assert_called_once_with(grpc.StatusCode.NOT_FOUND, "Job not found")

    @patch('processing.services.job_service.JobService.create_job')
    def test_create_job_grpc_redis_failure(self, mock_create):
        """Test that gRPC CreateJob calls context.abort with UNAVAILABLE when Redis fails."""
        # Setup mock
        mock_job = MagicMock()
        mock_job.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_create.return_value = (mock_job, False) # success=False
        
        servicer = JobServiceServicer()
        request = jobs_pb2.CreateJobRequest(
            nombre="Redis Failure Job",
            tipo="test",
            contenido="content",
            pipeline_config=[jobs_pb2.Stage(stage="extraction")]
        )
        context = MagicMock()
        context.abort.side_effect = Exception("Aborted")
        
        with pytest.raises(Exception, match="Aborted"):
            servicer.CreateJob(request, context)
            
        context.abort.assert_called_once()
        args, _ = context.abort.call_args
        assert args[0] == grpc.StatusCode.UNAVAILABLE
        assert "Failed to confirm enqueue in Redis" in args[1]
