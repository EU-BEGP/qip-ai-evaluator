# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.evaluations.models import Evaluation, Scan


class EvaluationStatusSerializer(serializers.ModelSerializer):
    """Serializes the status and relevant metadata of a full evaluation."""

    course_key = serializers.CharField(source='module.course_key', read_only=True)
    scan_name = serializers.SerializerMethodField()
    evaluation_id = serializers.CharField(source='id', read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Evaluation
        fields = ['status', 'course_key', 'scan_name', 'evaluation_id']

    @extend_schema_field(serializers.CharField)
    def get_scan_name(self, obj):
        return "All Scans"


class ScanStatusSerializer(serializers.ModelSerializer):
    """Serializes the status and relevant metadata of an individual scan."""

    course_key = serializers.CharField(source='evaluation.module.course_key', read_only=True)
    scan_name = serializers.CharField(source='scan_type', read_only=True)
    evaluation_id = serializers.CharField(source='evaluation.id', read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Scan
        fields = ['status', 'course_key', 'scan_name', 'evaluation_id']


class StartEvaluationSerializer(serializers.Serializer):
    """Validates evaluate input: resolves or creates the evaluation, then triggers RAG."""

    course_link = serializers.CharField(write_only=True)
    scan_name = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    message = serializers.CharField(read_only=True)
    scan_id = serializers.CharField(read_only=True)
    evaluation_id = serializers.CharField(read_only=True)


class WebhookCallbackSerializer(serializers.Serializer):
    """Uses relational fields to fetch full model instances from the payload."""

    evaluation_id = serializers.PrimaryKeyRelatedField(
        queryset=Evaluation.objects.all(),
        source='evaluation'
    )
    status = serializers.CharField(required=True)
    result = serializers.JSONField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)
    scan_names = serializers.ListField(child=serializers.CharField(), required=False)
