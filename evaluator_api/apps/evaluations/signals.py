# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.evaluations.models import Evaluation, Module
from apps.evaluations.services.rag_service import RagService

logger = logging.getLogger(__name__)


def _invalidate_module_cache(module):
    if module:
        try:
            RagService.invalidate_cache(module.course_key)
            logger.info(f"Invalidated RAG cache for module {module.course_key}")
        except Exception as e:
            logger.error(f"Error invalidating RAG cache for {module.course_key}: {e}")


@receiver([post_save, post_delete], sender=Evaluation)
def evaluation_changed(sender, instance, **kwargs):
    _invalidate_module_cache(instance.module)


@receiver([post_save, post_delete], sender=Module)
def module_changed(sender, instance, **kwargs):
    _invalidate_module_cache(instance)
