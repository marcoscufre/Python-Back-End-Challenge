import json
import time
from django.conf import settings
import redis

class EventPublisher:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.stream_name = 'job_events'

    def publish(self, event_type, job_id, payload=None, max_retries=3):
        event_data = {
            'job_id': str(job_id),
            'timestamp': str(time.time()),
            'event_type': event_type,
            'payload': json.dumps(payload or {})
        }
        
        for attempt in range(max_retries):
            try:
                # XADD publica el evento en el stream de Redis
                self.redis_client.xadd(self.stream_name, event_data)
                print(f"Published event: {event_type} for job {job_id}")
                return True
            except (redis.ConnectionError, redis.TimeoutError) as e:
                wait_time = (2 ** attempt)
                print(f"Error publishing to Redis (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        print(f"CRITICAL: Failed to publish event {event_type} for job {job_id} after {max_retries} attempts.")
        return False

publisher = EventPublisher()
