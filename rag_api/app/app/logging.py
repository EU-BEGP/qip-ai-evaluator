# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime:s} {name} {message}",
            "style": "{",
        },
        "verbose": {
            "format": "{levelname} {asctime:s} {name} {module}.py (line {lineno:d}) {funcName} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file_error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": BASE_DIR / "logs" / "rag.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB per file
            "backupCount": 5,
            "delay": True,
        },
    },
    "loggers": {
        "": {
            "level": "WARNING",
            "handlers": ["console", "file_error"],
        },
        "django": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "apps.evaluator": {
            "level": "INFO",
            "handlers": ["console", "file_error"],
            "propagate": False,
        },
        "rag": {
            "level": "INFO",
            "handlers": ["console", "file_error"],
            "propagate": False,
        },
        "retrievers": {
            "level": "INFO",
            "handlers": ["console", "file_error"],
            "propagate": False,
        },
        "document_processing": {
            "level": "INFO",
            "handlers": ["console", "file_error"],
            "propagate": False,
        },
        "model_wrapper": {
            "level": "INFO",
            "handlers": ["console", "file_error"],
            "propagate": False,
        },
        "celery": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
