from rest_framework import serializers
from .models import Job, JobStatus

class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['nombre', 'tipo', 'contenido', 'pipeline_config']

class JobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'nombre', 'tipo', 'status', 'results', 'created_at', 'updated_at']

class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'status', 'created_at']
