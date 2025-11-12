import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evaluator_api.settings')
app = Celery('evaluator_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()