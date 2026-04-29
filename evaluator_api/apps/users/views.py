# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404

from .serializers import RemoteLoginSerializer, UserProfileSerializer
from .services import AuthService
from .models import User

logger = logging.getLogger(__name__)


class Book4RLabLoginView(generics.GenericAPIView):
    """Exchanges an Book4RLab token for a local JWT."""
    
    serializer_class = RemoteLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        logger.info("New login attempt initiated.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        external_token = AuthService.user_remote_login(email, password)
        if not external_token:
            logger.warning("External auth rejected for user.")
            return Response({"error": "Invalid credentials in Book4RLab"}, status=status.HTTP_401_UNAUTHORIZED)

        user = AuthService.user_get_and_sync(external_token)
        if not user:
            logger.error("Profile sync failed after successful login.")
            return Response({"error": "Failed to sync user profile"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        refresh = RefreshToken.for_user(user)
        logger.info("Session established for user")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })


class UserProfileMeView(generics.RetrieveAPIView):
    """Retrieves the profile of the currently authenticated user."""
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        logger.debug(f"Profile access for user ID: {self.request.user.id}")
        return self.request.user


class UserProfileDetailView(generics.RetrieveAPIView):
    """Allows administrators to view a specific user's profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        target_pk = self.kwargs.get('pk')
        requesting_user = self.request.user

        if not requesting_user.is_staff:
            logger.warning(f"Security Alert: Non-admin {requesting_user.id} tried to access profile {target_pk}")
            self.permission_denied(
                self.request, 
                message="Only administrators can access this endpoint."
            )

        logger.info(f"Admin {requesting_user.id} accessing profile ID: {target_pk}")
        return get_object_or_404(User, pk=target_pk)
