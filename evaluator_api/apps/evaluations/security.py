# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework.request import Request
from django.conf import settings
import functools
from rest_framework.response import Response
from rest_framework import status

def verify_rag_callback(view_func):
    @functools.wraps(view_func)
    def _wrapped_view(request: Request, *args, **kwargs):
        provided_secret = request.headers.get('X-Callback-Secret')
        expected_secret = settings.RAG_CALLBACK_SECRET
        if not provided_secret or provided_secret != expected_secret:
            return Response({"error": "Unauthorized callback"}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return _wrapped_view