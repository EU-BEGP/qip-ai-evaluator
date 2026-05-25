# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Custom admin configuration for the Email-based User model

    ordering = ['email']
    list_display = ['id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_display_links = ['id', 'email']
    search_fields = ['email', 'first_name', 'last_name']
    list_filter = ['is_staff', 'is_active']
    readonly_fields = ['date_joined', 'updated_at', 'last_login']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'country', 'time_zone', 'external_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'is_staff', 'is_active'),
        }),
    )
