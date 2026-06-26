# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework import serializers

from .security import is_allowed_callback_url


class EvaluateModuleSerializer(serializers.Serializer):
    """Validates input for starting an asynchronous module evaluation."""

    course_key = serializers.CharField()
    callback_url = serializers.CharField()
    qip_user_id = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    evaluation_id = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    scan_names = serializers.ListField(child=serializers.CharField(), required=False, allow_null=True, default=None)
    previous_evaluation = serializers.JSONField(required=False, allow_null=True, default=None)
    existing_snapshot = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    run_id = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)

    def validate_callback_url(self, value):
        """Reject any callback target whose host is not explicitly allowlisted."""

        if not is_allowed_callback_url(value):
            raise serializers.ValidationError("callback_url host is not allowed.")
        return value


class CancelEvaluationSerializer(serializers.Serializer):
    """Validates input for cancelling a running evaluation task by run_id."""

    run_id = serializers.CharField()


class ModuleLastModifiedSerializer(serializers.Serializer):
    """Validates input for bulk last-modified date retrieval."""

    course_keys = serializers.ListField(child=serializers.CharField(), min_length=1)
    force = serializers.BooleanField(required=False, default=False)


class ModuleMetadataSerializer(serializers.Serializer):
    """Validates input for structured metadata extraction."""

    course_key = serializers.CharField()
