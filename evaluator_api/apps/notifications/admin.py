from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # Admin configuration for notifications
    list_display = ('id', 'user', 'title', 'is_read', 'created_at', 'scan_type')
    list_filter = ('is_read', 'created_at', 'scan_type')
    search_fields = ('title', 'content', 'user__email')
