import json
import time
from django.conf import settings
import redis

class EventPublisher:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.stream_name = 'job_events'

    def publish(self, event_type, job_id, payload=None):
        event_data = {
            'job_id': str(job_id),
            'timestamp': str(time.time()),
            'event_type': event_type,
            'payload': json.dumps(payload or {})
        }
        # XADD publica el evento en el stream de Redis
        self.redis_client.xadd(self.stream_name, event_data)
        print(f"Published event: {event_type} for job {job_id}")

publisher = EventPublisher()
