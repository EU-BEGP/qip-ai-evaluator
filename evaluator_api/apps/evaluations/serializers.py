# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework import serializers
from .models import Evaluation, Scan, Module, Criterion

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

class CriterionListSerializer(serializers.ModelSerializer):
    # Serialize the criteria
    question = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Criterion
        fields = ['id', 'criterion_name', 'question', 'description', 'user_selection']

    def get_rubric_data(self, obj):
        # Helper, search data from rubric
        try:
            # Criterion -> Scan -> Evaluation -> Rubric
            rubric = obj.scan.evaluation.rubric
            if not rubric or not rubric.content: 
                return {}
            
            content = rubric.content
            if isinstance(content, dict):
                content = content.get('scans', [])
            
            target_scan = next((s for s in content if s.get('scan') == obj.scan.scan_type), None)
            if not target_scan: return {}

            target_crit = next((c for c in target_scan.get('criteria', []) if c.get('name') == obj.criterion_name), None)
            return target_crit or {}
            
        except Exception:
            return {}

    def get_question(self, obj):
        return self.get_rubric_data(obj).get('review_question', 'No question available')

    def get_description(self, obj):
        return self.get_rubric_data(obj).get('description', '')

class CriterionUpdateSerializer(serializers.Serializer):
    # Validate user choice
    result = serializers.ChoiceField(
        choices=['YES', 'NO', 'NOT APPLICABLE', 'Yes', 'No', 'Not applicable', 'yes', 'no', 'not applicable']
    )
