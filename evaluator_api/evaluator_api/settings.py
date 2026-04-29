# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import os
import dj_database_url
from decouple import config
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab

from .logging import LOGGING


BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = config('ENVIRONMENT', default='production')
SECRET_KEY = config('SECRET_KEY')

# Debug is True ONLY if ENVIRONMENT is development
DEBUG = (ENVIRONMENT == 'development')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'corsheaders',
    'apps.users.apps.UsersConfig',
    'apps.evaluations.apps.EvaluationsConfig',
    'apps.notifications.apps.NotificationsConfig',
    'rest_framework_api_key'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'evaluator_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'evaluator_api.wsgi.application'


# Database
DB_NAME = config('POSTGRES_DB')
DB_USER = config('POSTGRES_USER')
DB_PASSWORD = config('POSTGRES_PASSWORD')
DB_HOST = config('DB_HOST', default='db')
DB_PORT = config('DB_PORT', default='5432')

DATABASES = {
    'default': dj_database_url.parse(
        f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        conn_max_age=600
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.User'

# DRF & JWT (Token) Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'QIP Evaluator API',
    'DESCRIPTION': 'API documentation for the QIP Evaluator V.2.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = config('STATIC_URL', default='/evaluator/api/static/')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# External API Endpoints
EXTERNAL_LOGIN_API_URL = config('EXTERNAL_LOGIN_API_URL')
EXTERNAL_AUTH_ME_URL = config('EXTERNAL_AUTH_ME_URL')

# RAG Construction
RAG_BASE_URL = config('RAG_BASE_URL').rstrip('/')
RAG_API_MODULE_MODIFIED_URL = f"{RAG_BASE_URL}/module_last_modified/"
RAG_API_EVALUATE_URL = f"{RAG_BASE_URL}/evaluate/"
RAG_API_METADATA_URL = f"{RAG_BASE_URL}/extract_metadata/"

RAG_CALLBACK_SECRET = config('RAG_CALLBACK_SECRET')
PUBLIC_BASE_URL = config('PUBLIC_BASE_URL', default="http://host.docker.internal:8004/")
FORCE_SCRIPT_NAME = config('FORCE_SCRIPT_NAME', default=None)

# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)

# Base Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:8004",
    "http://127.0.0.1:8004",
    "http://host.docker.internal:8004",
]

# Add extra origins from .env
raw_cors = config('CORS_ALLOWED_ORIGINS', default='')
origins = [u.strip() for u in raw_cors.split(',') if u.strip()]
if origins:
    CSRF_TRUSTED_ORIGINS.extend(origins)
    if not CORS_ALLOW_ALL_ORIGINS:
        CORS_ALLOWED_ORIGINS = origins

# Security settings for proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Celery Configuration
CELERY_BROKER_URL = "redis://broker:6379/0"
CELERY_RESULT_BACKEND = "redis://broker:6379/0"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://broker:6379/1",
    }
}

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-review-token",
    "x-badge-token"
]

# Email Configuration
if ENVIRONMENT == 'production':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD') 
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = f'QIP Evaluator Team <{EMAIL_HOST_USER}>'
    ACCOUNT_EMAIL_SUBJECT_PREFIX = '[QIP Evaluator]'
    SERVER_EMAIL = f'QIP Evaluator Team <{EMAIL_HOST_USER}>'
    EMAIL_SUBJECT_PREFIX = '[QIP Evaluator] '
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

ADMINS = [
    ('Admin', config('ADMIN_EMAIL'))
    ]

# Scheduled tasks with Celery
CELERY_BEAT_SCHEDULE = {
    'delete-old-messages-daily': {
        'task': 'apps.notifications.tasks.delete_old_messages',
        'schedule': crontab(hour=0, minute=0),
    },

    'cleanup-module-evaluations-daily': {
        'task': 'apps.evaluations.tasks.cleanup_module_evaluations',
        'schedule': crontab(hour=0, minute=30),
        'kwargs': {'limit': 4},
    },
}
