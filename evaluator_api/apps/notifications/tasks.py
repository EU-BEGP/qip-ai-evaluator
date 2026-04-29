# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from celery import shared_task
from datetime import timedelta

from django.utils import timezone

from .models import Message

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5 * 60})
def delete_old_messages(self):
    try:
        cutoff = timezone.now() - timedelta(days=30)
        deleted, _ = Message.objects.filter(created_at__lt=cutoff).delete()

        if deleted == 0:
            logger.info("No old messages to delete.")
        else:
            logger.info(f"Deleted {deleted} messages older than {cutoff}.")

    except Exception as e:
        logger.error(f"Error deleting old messages: {str(e)}")
        raise
