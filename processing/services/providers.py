import time
import abc
import random

class BaseProvider(abc.ABC):
    @abc.abstractmethod
    def process(self, input_data):
        pass

class ExtractionProvider(BaseProvider):
    def process(self, input_data):
        # input_data es el contenido crudo
        # Simular latencia base
        time.sleep(random.uniform(0.1, 0.3))
        return f"Extracted text from: {input_data[:50]}..."

class FastExtractor(ExtractionProvider):
    def process(self, input_data):
        time.sleep(0.1) # 100ms
        return super().process(input_data)

class SlowExtractor(ExtractionProvider):
    def process(self, input_data):
        time.sleep(2.0) # 2s
        return super().process(input_data)

class AnalysisProvider(BaseProvider):
    def process(self, input_data):
        # input_data es el texto extraído
        time.sleep(random.uniform(0.1, 0.5))
        return {
            "entities": ["entity1", "entity2"],
            "categories": ["cat1", "cat2"]
        }

class EnrichmentProvider(BaseProvider):
    def process(self, input_data):
        # input_data son las entidades/categorías
        time.sleep(random.uniform(0.1, 0.5))
        return {
            "metadata": "enriched data",
            "confidence": 0.98
        }

def get_provider(stage_name, config=None):
    # Fábrica de proveedores basada en la configuración
    if stage_name == 'extraction':
        variant = config.get('variant', 'fast') if config else 'fast'
        return SlowExtractor() if variant == 'slow' else FastExtractor()
    elif stage_name == 'analysis':
        return AnalysisProvider()
    elif stage_name == 'enrichment':
        return EnrichmentProvider()
    return None
