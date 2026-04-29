# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializes notifications for the mailbox view."""

    scan_name = serializers.CharField(source='scan_type', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'user_id',
            'title',
            'content',
            'is_read',
            'created_at',
            'evaluation_id',
            'scan_name',
        ]


class MarkReadSerializer(serializers.Serializer):
    """Validates input for marking a message as read."""

    message_id = serializers.IntegerField(required=True, write_only=True)


class UnreadCountSerializer(serializers.Serializer):
    """Serializes the count of unread notifications."""

    quantity = serializers.IntegerField(read_only=True)
