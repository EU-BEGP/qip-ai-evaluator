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
        """Pre-load shared AI resources, but only under Gunicorn.

        Gunicorn --preload builds the KB once in the master process; forked
        workers inherit it via copy-on-write. Every other entrypoint is skipped
        here: the Celery worker loads the KB lazily via tasks.shared, and one-off
        commands (runserver, shell, test) must not pull the heavy AI stack.
        """

        if "gunicorn" not in sys.argv[0]:
            return

        try:
            from .bootstrap import build_knowledge_base_auto, load_criteria_auto

            logger.info("[STARTUP] Pre-loading shared AI resources...")
            build_knowledge_base_auto()
            load_criteria_auto()
            logger.info("[STARTUP] Shared AI resources ready.")

        except Exception as e:
            logger.error(f"[STARTUP] Failed to pre-load AI resources: {e}", exc_info=True)
