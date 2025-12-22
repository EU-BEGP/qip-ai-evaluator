from rest_framework import serializers
from .models import Evaluation, Scan, Module

class ModuleSerializer(serializers.ModelSerializer):
    # Serializes the raw Module data
    class Meta:
        model = Module
        fields = ['id', 'course_key', 'title', 'created_at', 'updated_at']

class ScanSerializer(serializers.ModelSerializer):
    # Serializes individual Scan objects
    class Meta:
        model = Scan
        fields = ['id', 'scan_type', 'status', 'result_json']

class EvaluationDetailSerializer(serializers.ModelSerializer):
    # Serializes full evaluation details including nested scans and module
    scans = ScanSerializer(many=True, read_only=True)
    module = ModuleSerializer(read_only=True)
    formatted_date = serializers.ReadOnlyField()

    class Meta:
        model = Evaluation
        fields = [
            'id', 
            'status', 
            'created_at', 
            'formatted_date', 
            'title', 
            'error_message', 
            'module', 
            'scans', 
            'result_json'
        ]

class StartEvaluationSerializer(serializers.Serializer):
    # Serializes the Evaluation
    course_link = serializers.URLField(required=True)
    email = serializers.EmailField(required=True)
    scan_name = serializers.CharField(required=False, allow_null=True)
    evaluation_id = serializers.IntegerField(required=False, allow_null=True)
