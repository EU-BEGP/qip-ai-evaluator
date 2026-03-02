import functools
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from .models import ExternalReview 

def verify_review_token(view_func):
    # Ensure the provided UUID token in headers is valid and not completed
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = request.headers.get('X-Review-Token')
        if not token:
            return Response(
                {"error": "Authentication credentials (X-Review-Token) were not provided."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        try:
            review_session = ExternalReview.objects.get(token=token)
        # 2. Catch formatting errors
        except (ExternalReview.DoesNotExist, ValidationError, ValueError):
            return Response(
                {"error": "Invalid or non-existent token."}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        if review_session.is_completed:
            return Response( 
                {"error": "This review session has already been completed."}, 
                status=status.HTTP_410_GONE
            )
        return view_func(request, review_session, *args, **kwargs)
        
    return _wrapped_view
