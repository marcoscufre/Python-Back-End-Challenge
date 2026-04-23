from rest_framework import serializers
from .models import Job, JobStatus

class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['nombre', 'tipo', 'contenido', 'pipeline_config']

    def validate_pipeline_config(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("pipeline_config must be a list.")
        
        if len(value) > 3:
            raise serializers.ValidationError("The pipeline cannot have more than 3 stages.")
            
        valid_stages = {'extraction', 'analysis', 'enrichment'}
        for item in value:
            if isinstance(item, str):
                stage_name = item
            elif isinstance(item, dict):
                stage_name = item.get('stage')
            else:
                raise serializers.ValidationError(f"Invalid item format in pipeline: {item}. Must be string or object.")
                
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
