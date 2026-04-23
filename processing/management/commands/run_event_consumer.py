import json
import time
import redis
from django.core.management.base import BaseCommand
from django.conf import settings
from processing.models import Job, JobStatus
from processing.services.events import publisher
from processing.services.providers import get_provider

class Command(BaseCommand):
    help = 'Runs the event consumer for processing jobs'

    def __init__(self):
        super().__init__()
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.stream_name = 'job_events'
        self.group_name = 'processing_group'
        self.consumer_name = 'consumer_1'

    def handle(self, *args, **options):
        self.setup_consumer_group()
        self.stdout.write(self.style.SUCCESS(f'Orchestrator started (consumer: {self.consumer_name}). Waiting for events...'))

        while True:
            try:
                # 0. Reclamar mensajes huérfanos de otros consumidores inactivos por más de 10s (XAUTOCLAIM)
                try:
                    claim_res = self.redis_client.xautoclaim(
                        self.stream_name, self.group_name, self.consumer_name, 10000, start_id='0-0', count=5
                    )
                    if claim_res and len(claim_res) >= 2 and claim_res[1]:
                        for msg_id, data in claim_res[1]:
                            self.stdout.write(self.style.WARNING(f"Claimed orphaned message {msg_id}"))
                            self.process_event(msg_id, data)
                            self.redis_client.xack(self.stream_name, self.group_name, msg_id)
                except Exception as e:
                    # Lo silenciamos en caso de que ocurra algún error temporal o versión de Redis vieja
                    pass

                # 1. Primero intentar leer mensajes pendientes (que fueron entregados pero no confirmados)
                # Usamos ID='0' para leer mensajes en el PEL (Pending Entires List) de este consumidor
                messages = self.redis_client.xreadgroup(
                    self.group_name, self.consumer_name, {self.stream_name: '0'}, count=1
                )

                # 2. Si no hay mensajes pendientes, leer nuevos ('>')
                if not messages or not messages[0][1]:
                    messages = self.redis_client.xreadgroup(
                        self.group_name, self.consumer_name, {self.stream_name: '>'}, count=1, block=5000
                    )

                if messages:
                    for stream, msgs in messages:
                        for msg_id, data in msgs:
                            self.process_event(msg_id, data)
                            # Acknowledgment
                            self.redis_client.xack(self.stream_name, self.group_name, msg_id)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error in consumer loop: {e}"))
                time.sleep(1)

    def setup_consumer_group(self):
        try:
            self.redis_client.xgroup_create(self.stream_name, self.group_name, id='0', mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise e

    def process_event(self, msg_id, data):
        event_type = data[b'event_type'].decode('utf-8')
        job_id = data[b'job_id'].decode('utf-8')
        
        if event_type == 'job.created':
            self.run_pipeline(job_id)

    def run_pipeline(self, job_id):
        try:
            job = Job.objects.get(id=job_id)
            if job.status != JobStatus.PENDING:
                return

            job.status = JobStatus.PROCESSING
            job.save()
            
            payload = job.contenido
            results = {}

            # El pipeline_config es una lista de etapas, ej: ["extraction", "analysis"]
            # O una lista de dicts con config: [{"stage": "extraction", "config": {"variant": "slow"}}]
            pipeline = job.pipeline_config
            
            for stage_info in pipeline:
                # Recargar job para verificar si fue cancelado
                job.refresh_from_db()
                if job.status == JobStatus.CANCELLED:
                    self.stdout.write(self.style.WARNING(f"Job {job_id} was cancelled. Stopping pipeline."))
                    return

                stage_name = stage_info if isinstance(stage_info, str) else stage_info.get('stage')
                stage_config = {} if isinstance(stage_info, str) else stage_info.get('config', {})

                publisher.publish('job.stage_started', job_id, {'stage': stage_name})
                
                # Ejecutar con Resiliencia (Retry con Backoff)
                result = self.execute_with_retry(stage_name, stage_config, payload)
                
                if result is None:
                    job.status = JobStatus.FAILED
                    job.save()
                    publisher.publish('job.failed', job_id, {'error': f"Stage {stage_name} failed after retries"})
                    return

                results[stage_name] = result
                job.results = results
                job.save()
                
                publisher.publish('job.stage_completed', job_id, {
                    'stage': stage_name,
                    'result': result
                })
                
                # El output de una etapa es el input de la siguiente (si aplica)
                payload = result

            job.status = JobStatus.COMPLETED
            job.save()
            publisher.publish('job.completed', job_id)

        except Job.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Job {job_id} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error in pipeline for job {job_id}: {e}"))
            Job.objects.filter(id=job_id).update(status=JobStatus.FAILED)
            publisher.publish('job.failed', job_id, {'error': str(e)})

    def execute_with_retry(self, stage_name, stage_config, payload, max_retries=3):
        for attempt in range(max_retries):
            try:
                provider = get_provider(stage_name, stage_config)
                if not provider:
                    return None
                return provider.process(payload)
            except Exception as e:
                wait_time = (2 ** attempt) # Exponential backoff: 1s, 2s, 4s
                self.stdout.write(self.style.WARNING(f"Retry {attempt+1}/{max_retries} for {stage_name}. Waiting {wait_time}s..."))
                time.sleep(wait_time)
        return None
