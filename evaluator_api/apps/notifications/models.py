# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.db import models
from django.conf import settings

class Message(models.Model):
    # Represents a notification sent to a user regarding an evaluation update
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages')
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    evaluation = models.ForeignKey(
        'evaluations.Evaluation', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='messages'
    )
    scan_type = models.CharField(max_length=100, null=True, blank=True)
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message {self.id} for {self.user.email}"
