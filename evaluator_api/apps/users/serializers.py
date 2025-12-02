from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    # Serializes User model data for responses
    class Meta:
        model = User
        fields = ['id', 'email', 'is_staff', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined', 'is_staff', 'is_active']

class LoginInputSerializer(serializers.Serializer):
    # Validates input payload for the login endpoint
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
