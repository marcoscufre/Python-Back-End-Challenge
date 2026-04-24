import grpc
from concurrent import futures
import time
import json
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from ...proto import jobs_pb2, jobs_pb2_grpc
from ...services.job_service import JobService
from django.conf import settings

class JobServiceServicer(jobs_pb2_grpc.JobServiceServicer):
    def CreateJob(self, request, context):
        # ... (mapping logic)
        pipeline_config = []
        for stage in request.pipeline_config:
            item = {'stage': stage.stage}
            if stage.variant:
                item['config'] = {'variant': stage.variant}
            pipeline_config.append(item)
        
        try:
            job, success = JobService.create_job(
                nombre=request.nombre,
                tipo=request.tipo,
                contenido=request.contenido,
                pipeline_config=pipeline_config
            )
            
            if not success:
                context.abort(
                    grpc.StatusCode.UNAVAILABLE, 
                    "Failed to confirm enqueue in Redis. The job was created in database but might not start automatically."
                )
                return jobs_pb2.CreateJobResponse()

            return jobs_pb2.CreateJobResponse(job_id=str(job.id), error="")
        except ValidationError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
            return jobs_pb2.CreateJobResponse()
        except Exception as e:
            # Si el error ya viene de un context.abort (común en tests o logic avanzada),
            # no re-abortamos para evitar inconsistencias.
            if "Aborted" in str(e):
                raise e
            context.abort(grpc.StatusCode.INTERNAL, str(e))
            return jobs_pb2.CreateJobResponse()

    def GetJob(self, request, context):
        job = JobService.get_job(request.job_id)
        if not job:
            context.abort(grpc.StatusCode.NOT_FOUND, "Job not found")
            return jobs_pb2.GetJobResponse() # Nunca llega aquí
        
        job_msg = jobs_pb2.JobMessage(
            id=str(job.id),
            nombre=job.nombre,
            tipo=job.tipo,
            status=job.status,
            results_json=json.dumps(job.results),
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat()
        )
        return jobs_pb2.GetJobResponse(job=job_msg, error="")

class Command(BaseCommand):
    help = 'Runs the gRPC server'

    def handle(self, *args, **options):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        jobs_pb2_grpc.add_JobServiceServicer_to_server(JobServiceServicer(), server)
        
        port = "50051"
        server.add_insecure_port(f'[::]:{port}')
        self.stdout.write(self.style.SUCCESS(f'Starting gRPC server on port {port}...'))
        server.start()
        
        try:
            while True:
                time.sleep(86400)
        except KeyboardInterrupt:
            server.stop(0)
