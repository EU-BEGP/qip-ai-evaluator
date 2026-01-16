# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from .celery import app as celery_app

# The app is always imported when
# Django starts so that shared_task will use this app.
__all__ = ('celery_app',)
