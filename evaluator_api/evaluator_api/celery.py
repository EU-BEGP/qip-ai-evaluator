# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evaluator_api.settings')
app = Celery('evaluator_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()