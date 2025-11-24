from django.apps import AppConfig
import sys
import logging

logger = logging.getLogger(__name__)

class EvaluatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluator'

    def ready(self):
        """
        Pre-load AI models into memory when Gunicorn/Django starts.
        """
        # Avoid running twice during dev reload
        if 'runserver' not in sys.argv:
            # Import using relative path or full path depending on structure
            # Assuming init_knowledge.py is in the same folder (app/evaluator)
            try:
                from .init_knowledge import build_knowledge_base_auto, load_criteria_auto
                
                logger.info("🚀 [PRE-LOAD] Initializing Shared AI Memory...")
                
                # This triggers the Singletons
                build_knowledge_base_auto()
                load_criteria_auto()
                
                logger.info("✅ [PRE-LOAD] AI Models loaded.")
            except ImportError as e:
                logger.error(f"Failed to pre-load AI models: {e}")
