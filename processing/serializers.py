from rest_framework import serializers
from .models import Job, JobStatus

class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['nombre', 'tipo', 'contenido', 'pipeline_config']

    def validate_pipeline_config(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("pipeline_config must be a list.")
        valid_stages = {'extraction', 'analysis', 'enrichment'}
        for item in value:
            stage_name = item if isinstance(item, str) else item.get('stage')
            if not stage_name or stage_name not in valid_stages:
                raise serializers.ValidationError(f"Invalid stage '{stage_name}'. Allowed: {', '.join(valid_stages)}.")
        return value

class JobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'nombre', 'tipo', 'status', 'results', 'created_at', 'updated_at']

class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'status', 'created_at']
