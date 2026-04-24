from typing import List, Dict, Any, Optional, Tuple
from django.core.exceptions import ValidationError
from ..models import Job, JobStatus
from .events import publisher

class JobService:
    @staticmethod
    def validate_input(nombre: str, tipo: str, contenido: str, pipeline_config: Any) -> Dict[str, Any]:
        errors = {}
        if not nombre or not isinstance(nombre, str) or len(nombre) > 255:
            errors['nombre'] = "Invalid name. Must be a non-empty string up to 255 characters."
        
        if not tipo or not isinstance(tipo, str) or len(tipo) > 100:
            errors['tipo'] = "Invalid type. Must be a non-empty string up to 100 characters."
            
        if not contenido or not isinstance(contenido, str):
            errors['contenido'] = "Content must be a non-empty string."

        if not isinstance(pipeline_config, list):
            errors['pipeline_config'] = "pipeline_config must be a list."
        elif len(pipeline_config) > 3:
            errors['pipeline_config'] = "The pipeline cannot have more than 3 stages."
        else:
            valid_stages = {'extraction', 'analysis', 'enrichment'}
            validated_pipeline = []
            for item in pipeline_config:
                if isinstance(item, str):
                    stage_name = item
                    config = {}
                elif isinstance(item, dict):
                    stage_name = item.get('stage')
                    config = item.get('config', {})
                    if not config and 'variant' in item:
                        config = {'variant': item['variant']}
                else:
                    errors['pipeline_config'] = f"Invalid item format in pipeline: {item}. Must be string or object."
                    break
                    
                if not stage_name or stage_name not in valid_stages:
                    errors['pipeline_config'] = f"Invalid stage '{stage_name}'. Allowed: {', '.join(valid_stages)}."
                    break
                
                validated_pipeline.append({
                    'stage': stage_name,
                    'config': config
                })
        
        if errors:
            raise ValidationError(errors)
            
        return {
            'nombre': nombre,
            'tipo': tipo,
            'contenido': contenido,
            'pipeline_config': validated_pipeline
        }

    @staticmethod
    def create_job(nombre: str, tipo: str, contenido: str, pipeline_config: List[Any]) -> Tuple[Job, bool]:
        # Validar y normalizar inputs
        clean_data = JobService.validate_input(nombre, tipo, contenido, pipeline_config)
        
        # Crear job
        job = Job.objects.create(
            nombre=clean_data['nombre'],
            tipo=clean_data['tipo'],
            contenido=clean_data['contenido'],
            pipeline_config=clean_data['pipeline_config']
        )
        
        # Publicar evento job.created
        success = publisher.publish('job.created', job.id, {
            'nombre': job.nombre,
            'tipo': job.tipo,
            'pipeline_config': job.pipeline_config
        })
        
        return job, success

    @staticmethod
    def get_job(job_id: str) -> Optional[Job]:
        try:
            return Job.objects.get(id=job_id)
        except (Job.DoesNotExist, ValidationError):
            return None
