# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import hmac
import logging
import functools

from rest_framework.request import Request
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

from apps.evaluations.models import Evaluation, Scan, UserModule

logger = logging.getLogger(__name__)


def verify_rag_callback(view_func):
    @functools.wraps(view_func)
    def _wrapped_view(request: Request, *args, **kwargs):
        provided_secret = request.headers.get('X-Callback-Secret') or ""
        expected_secret = settings.RAG_CALLBACK_SECRET or ""
        if not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
            logger.warning(
                "Unauthorized RAG callback rejected "
                f"(secret {'missing' if not provided_secret else 'mismatch'})"
            )
            return Response({"error": "Unauthorized callback"}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def has_module_access(user, module):
    """True when the user follows the given module."""

    if module is None or not getattr(user, "is_authenticated", False):
        return False
    return UserModule.objects.filter(user=user, module=module).exists()


def has_evaluation_access(user, evaluation):
    """True when the user may read the given evaluation (and its scans)."""

    return has_module_access(user, getattr(evaluation, "module", None))


def accessible_evaluations(user):
    """Evaluations the user is allowed to read."""

    if not getattr(user, "is_authenticated", False):
        return Evaluation.objects.none()
    return Evaluation.objects.filter(module__followed_by__user=user)


def accessible_scans(user):
    """Scans the user is allowed to read."""

    if not getattr(user, "is_authenticated", False):
        return Scan.objects.none()
    return Scan.objects.filter(evaluation__module__followed_by__user=user)
