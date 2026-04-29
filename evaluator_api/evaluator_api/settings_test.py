# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import os

# Seed all required config() vars before settings.py loads them.
# python-decouple raises UndefinedValueError for any config() call without a
# default if the key is missing from the environment and no .env file exists.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("EXTERNAL_LOGIN_API_URL", "http://test.invalid/login/")
os.environ.setdefault("EXTERNAL_AUTH_ME_URL", "http://test.invalid/me/")
os.environ.setdefault("RAG_BASE_URL", "http://test.invalid/rag")
os.environ.setdefault("RAG_CALLBACK_SECRET", "test-callback-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.invalid")

from .settings import *  # noqa: E402, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Console-only logging — prevents RotatingFileHandler FileNotFoundError when
# the logs/ directory does not exist (fresh clone, CI).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# Disable Celery during tests (tasks become synchronous no-ops)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
