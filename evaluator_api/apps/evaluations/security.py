# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework.request import Request
from django.conf import settings
from django.core.exceptions import ValidationError
import functools
from rest_framework.response import Response
from rest_framework import status
from apps.reviews.models import ExternalReview
from .models import Certificate 

def verify_rag_callback(view_func):
    @functools.wraps(view_func)
    def _wrapped_view(request: Request, *args, **kwargs):
        provided_secret = request.headers.get('X-Callback-Secret')
        expected_secret = settings.RAG_CALLBACK_SECRET
        if not provided_secret or provided_secret != expected_secret:
            return Response({"error": "Unauthorized callback"}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def verify_jwt_or_review_token(view_func):
    # Checks access by X-Review-Token (Priority) or JWT
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Try by Magic Token first (Priority for external reviewers)
        token = request.headers.get('X-Review-Token')
        if token:
            try:
                review_session = ExternalReview.objects.get(token=token)
                
                if review_session.is_completed:
                    return Response( 
                        {"error": "This review session has already been completed."}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                # External reviewer case
                return view_func(request, review_session=review_session, *args, **kwargs)
                
            # 1.2 Catch the formatting errors
            except (ExternalReview.DoesNotExist, ValidationError, ValueError):
                return Response(
                    {"error": "Invalid or non-existent review token."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

        # 2. Try by JWT validation (Fallback for admins/owners)
        if request.user and request.user.is_authenticated:
            return view_func(request, review_session=None, *args, **kwargs)

        # 3. No credentials provided
        return Response(
            {"error": "Authentication required. Provide a valid Bearer JWT or X-Review-Token."}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
        
    return _wrapped_view

def verify_badge_token(view_func):
    # Validates the X-Badge-Token header and injects the Certificate object
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = request.headers.get('X-Badge-Token')
        if not token:
            return Response(
                {"error": "X-Badge-Token header is missing"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            certificate = Certificate.objects.get(public_token=token)
            return view_func(request, certificate=certificate, *args, **kwargs)
            
        except (ValueError, ValidationError):
            # Catch Errors
            return Response(
                {"error": "Invalid badge token format"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            # Certificate does not exist
            return Response(
                {"error": "Badge token not found or expired"}, 
                status=status.HTTP_404_NOT_FOUND
            ) 
    return _wrapped_view
