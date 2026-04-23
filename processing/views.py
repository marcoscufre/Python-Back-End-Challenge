from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Job, JobStatus
from .serializers import JobCreateSerializer, JobDetailSerializer, JobListSerializer

from .services.events import publisher

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JobCreateSerializer
        if self.action == 'list':
            return JobListSerializer
        return JobDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        
        # Publicar evento job.created
        success = publisher.publish('job.created', job.id, {
            'nombre': job.nombre,
            'tipo': job.tipo,
            'pipeline_config': job.pipeline_config
        })
        
        if not success:
            job_id = job.id
            job.delete() # Revertir si no se pudo encolar para mantener consistencia
            return Response(
                {"error": "Failed to enqueue job in Redis. Broker might be down."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response({"job_id": job.id}, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return Response(
                {"error": f"Cannot cancel job in state {job.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = job.status
        job.status = JobStatus.CANCELLED
        job.save()
        
        # Publicar evento job.cancelled
        success = publisher.publish('job.cancelled', job.id)
        if not success:
            job.status = old_status
            job.save()
            return Response(
                {"error": "Failed to publish cancellation event. Broker might be down."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response({"status": "job cancelled"})
