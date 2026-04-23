import json
import time
import redis
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Runs a downstream consumer that logs all events'

    def __init__(self):
        super().__init__()
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.stream_name = 'job_events'
        self.group_name = 'downstream_group'
        self.consumer_name = 'downstream_1'

    def handle(self, *args, **options):
        self.setup_consumer_group()
        self.stdout.write(self.style.SUCCESS(f'Downstream consumer started (consumer: {self.consumer_name}). Listening on {self.stream_name}...'))

        while True:
            try:
                # 0. Reclamar mensajes huérfanos de otros consumidores inactivos por más de 10s
                try:
                    claim_res = self.redis_client.xautoclaim(
                        self.stream_name, self.group_name, self.consumer_name, 10000, start_id='0-0', count=5
                    )
                    if claim_res and len(claim_res) >= 2 and claim_res[1]:
                        for msg_id, data in claim_res[1]:
                            self.process_msg(msg_id, data, claimed=True)
                            self.redis_client.xack(self.stream_name, self.group_name, msg_id)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"XAUTOCLAIM failed: {e}"))

                # 1. Leer mensajes pendientes asignados a este consumidor
                messages = self.redis_client.xreadgroup(
                    self.group_name, self.consumer_name, {self.stream_name: '0'}, count=5
                )

                # 2. Si no hay pendientes, leer nuevos ('>')
                if not messages or not messages[0][1]:
                    messages = self.redis_client.xreadgroup(
                        self.group_name, self.consumer_name, {self.stream_name: '>'}, count=10, block=5000
                    )

                if messages:
                    for stream, msgs in messages:
                        for msg_id, data in msgs:
                            self.process_msg(msg_id, data)
                            # Acknowledgment
                            self.redis_client.xack(self.stream_name, self.group_name, msg_id)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error in downstream consumer: {e}"))
                time.sleep(1)

    def process_msg(self, msg_id, data, claimed=False):
        event_type = data[b'event_type'].decode('utf-8')
        job_id = data[b'job_id'].decode('utf-8')
        payload = data[b'payload'].decode('utf-8')
        prefix = "[CLAIMED EVENT]" if claimed else "[EVENT]"
        
        self.stdout.write(self.style.HTTP_INFO(
            f"{prefix} type={event_type} job={job_id} payload={payload}"
        ))

    def setup_consumer_group(self):
        try:
            self.redis_client.xgroup_create(self.stream_name, self.group_name, id='0', mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise e
