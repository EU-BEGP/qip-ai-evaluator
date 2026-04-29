# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class RemoteLoginSerializer(serializers.Serializer):
    """Validates input for the Book4RLab authentication handshake."""
    
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Standard serializer for user profile management."""

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'country',
            'time_zone',
            'is_staff',
        ]
        read_only_fields = ['id', 'email', 'is_staff']
