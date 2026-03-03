# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Message
from .serializers import MessageSerializer, MarkReadSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_mailbox(request, email):
    # Returns the top 20 notifications for a user, sorted by unread first
    if request.user.email != email:
        return Response({"error": "Access denied to this mailbox."}, status=status.HTTP_403_FORBIDDEN)

    messages = Message.objects.filter(user=request.user).order_by('is_read', '-created_at')[:20]
    data = [
        {
            "id": msg.id,
            "user_id": msg.user_id,
            "title": msg.title,
            "content": msg.content,
            "read": msg.is_read,
            "created_at": msg.created_at,
            "evaluation_id": msg.evaluation_id,
            "scan_name": msg.scan_type,
            "reviewer_id": msg.reviewer_id,
            "type": msg.type
        }
        for msg in messages
    ]
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_read(request):
    # Marks a specific message as read
    serializer = MarkReadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    if request.user.email != data['email']:
        return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

    message = get_object_or_404(Message, id=data['message_id'], user=request.user)
    message.is_read = True
    message.save()
    
    return Response({"message": "Message marked as read."}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_notifications_count(request, email):
    # Returns the count of unread messages
    if request.user.email != email:
        return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

    count = Message.objects.filter(user=request.user, is_read=False).count()
    return Response({"quantity": count}, status=status.HTTP_200_OK)
