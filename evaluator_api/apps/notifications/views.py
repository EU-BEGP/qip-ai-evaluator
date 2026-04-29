# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Message
from .serializers import MessageSerializer, MarkReadSerializer, UnreadCountSerializer


class UserMailboxView(APIView):
    """Returns the top 20 notifications for a user sorted by unread first."""

    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get(self, request):
        messages = Message.objects.filter(user=request.user).order_by('is_read', '-created_at')[:20]
        serializer = self.serializer_class(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessageMarkReadView(APIView):
    """Marks a specific message as read."""

    permission_classes = [IsAuthenticated]
    serializer_class = MarkReadSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        message = get_object_or_404(
            Message,
            id=data['message_id'],
            user=request.user
        )
        
        if not message.is_read:
            message.is_read = True
            message.save(update_fields=["is_read"])

        return Response({"message": "Message marked as read."}, status=status.HTTP_200_OK)


class NotificationsUnreadCountView(APIView):
    """Returns the count of unread messages for a user."""

    permission_classes = [IsAuthenticated]
    serializer_class = UnreadCountSerializer

    def get(self, request):
        quantity = Message.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        serializer = self.serializer_class({"quantity": quantity})
        return Response(serializer.data, status=status.HTTP_200_OK)
