# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.contrib import admin
from .models import Module, Evaluation, Scan, UserModule

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    # Admin for Global Modules
    list_display = ('id', 'course_key', 'title', 'updated_at')
    search_fields = ('course_key', 'title')

@admin.register(UserModule)
class UserModuleAdmin(admin.ModelAdmin):
    # Admin for User-Module links (Dashboard items)
    list_display = ('user', 'module', 'last_accessed')
    list_filter = ('user',)

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    # Admin for Evaluations
    list_display = ('id', 'module', 'status', 'triggered_by', 'formatted_date')
    list_filter = ('status', 'created_at')

@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    # Admin for Scans
    list_display = ('id', 'scan_type', 'status', 'evaluation')
    list_filter = ('scan_type', 'status')
