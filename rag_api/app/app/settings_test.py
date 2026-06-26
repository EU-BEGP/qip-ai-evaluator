# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import os

# Seed required config() vars before settings.py loads. decouple reads os.environ
# first, so these win in tests while real .env values still apply in deployment.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("QIP_CALLBACK_SECRET", "test-callback-secret")
os.environ.setdefault("RAG_INBOUND_SECRET", "test-inbound-secret")
os.environ.setdefault("ALLOWED_CALLBACK_HOSTS", "localhost,127.0.0.1,host.docker.internal")

from .settings import *

# Empty inline URLconf — the real one imports views.py (heavy RAG/AI stack) at load.
ROOT_URLCONF = []

# In-memory cache — never touch the Redis broker during tests.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Console-only logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
