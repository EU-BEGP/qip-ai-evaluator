# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class EvaluatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.evaluator"

    def ready(self):
        """
        Pre-load shared AI resources when Django starts.

        With Gunicorn --preload, this runs once in the master process.
        Forked workers inherit the loaded singletons via copy-on-write,
        avoiding redundant model loading per worker.

        Skipped during 'runserver' to avoid double-loading on dev autoreload.
        """
        
        if "runserver" in sys.argv:
            return

        try:
            from .init_knowledge import build_knowledge_base_auto, load_criteria_auto

            logger.info("[STARTUP] Pre-loading shared AI resources...")
            build_knowledge_base_auto()
            load_criteria_auto()
            logger.info("[STARTUP] Shared AI resources ready.")

        except Exception as e:
            logger.error(f"[STARTUP] Failed to pre-load AI resources: {e}", exc_info=True)
