# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.db import models
from django.conf import settings


class Message(models.Model):
    """Model representing a notification message for users."""

    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        ERROR = "ERROR", "Error"

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages')
    title = models.CharField(max_length=255)
    content = models.TextField()
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    evaluation = models.ForeignKey('evaluations.Evaluation', on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    scan_type = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message {self.id} for {self.user.email}"
