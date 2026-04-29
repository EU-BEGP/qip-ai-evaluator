# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.contrib import admin
from .models import Module, Evaluation, Scan, UserModule, Rubric


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'course_key', 'course_link', 'title', 'updated_at')
    search_fields = ('course_key', 'course_link', 'title')


@admin.register(UserModule)
class UserModuleAdmin(admin.ModelAdmin):
    list_display = ('user', 'module', 'last_accessed')
    list_filter = ('user',)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'module', 'status', 'triggered_by', 'formatted_date')
    list_filter = ('status', 'created_at')


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('id', 'scan_type', 'status', 'evaluation')
    list_filter = ('scan_type', 'status')


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'is_active_display', 'scans_count')
    ordering = ('-created_at',)
    readonly_fields = ('rubric_map', 'content_hash')

    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.boolean = True
    is_active_display.short_description = "Is Active"

    def scans_count(self, obj):
        return len(obj.available_scans)
    scans_count.short_description = "Scans"
