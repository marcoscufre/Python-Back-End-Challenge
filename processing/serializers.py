from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Job, JobStatus
from .services.job_service import JobService

class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['nombre', 'tipo', 'contenido', 'pipeline_config']

    def validate(self, data):
        try:
            # Validamos todo el conjunto de datos usando el servicio centralizado
            clean_data = JobService.validate_input(
                nombre=data.get('nombre'),
                tipo=data.get('tipo'),
                contenido=data.get('contenido'),
                pipeline_config=data.get('pipeline_config')
            )
            return clean_data
        except ValidationError as e:
            # Si es una ValidationError de Django con un dict de errores, DRF lo entiende si se lo pasamos
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        except Exception as e:
            raise serializers.ValidationError(str(e))

class JobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'nombre', 'tipo', 'status', 'results', 'created_at', 'updated_at']

class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'status', 'created_at']
