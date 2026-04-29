# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework import serializers

from apps.evaluations.models import Module, Evaluation
from apps.evaluations.services.overview_service import DashboardService


class DashboardModuleSerializer(serializers.ModelSerializer):
    """Serializer to represent the overview of a module on the dashboard."""

    link = serializers.CharField(source='course_key')
    last_modify = serializers.CharField(read_only=True)
    last_evaluation = serializers.CharField(read_only=True)
    last_average = serializers.FloatField(read_only=True)
    last_max = serializers.SerializerMethodField()
    last_evaluation_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    keywords = serializers.ListField(child=serializers.CharField(), read_only=True)
    scan_status = serializers.SerializerMethodField()
    ilos = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            'title', 'link', 'last_modify', 'last_evaluation',
            'last_average', 'last_max', 'last_evaluation_id',
            'status', 'keywords', 'scan_status', 'ilos'
        ]

    def get_last_max(self, obj) -> float:
        return 5

    def get_scan_status(self, obj):
        eval_obj = self.context.get("latest_eval_map", {}).get(obj.id)
        if not eval_obj:
            return []
        return [
            {"scan": scan.scan_type, "status": scan.get_status_display()}
            for scan in eval_obj.scans.all()
        ]

    def get_ilos(self, obj):
        eval_obj = self.context.get("latest_eval_map", {}).get(obj.id)
        if not eval_obj or not eval_obj.metadata_json:
            return []
        source = eval_obj.metadata_json.get("ilos", eval_obj.metadata_json)
        return [
            {"name": "Knowledge", "eqf_lvl": source.get("suggested_knowledge", "N/A")},
            {"name": "Skills", "eqf_lvl": source.get("suggested_skills", "N/A")},
            {"name": "RA", "eqf_lvl": source.get("suggested_ra", "N/A")},
        ]

    def to_representation(self, obj):
        data = super().to_representation(obj)
        eval_obj = self.context["latest_eval_map"].get(obj.id)
        rag_date = self.context["rag_map"].get(obj.course_key)
        data["last_modify"] = DashboardService._rag_date_to_utc_display(rag_date)
        data["last_evaluation"] = eval_obj.created_at.strftime("%Y-%m-%d %H:%M") if eval_obj else None
        data["last_evaluation_id"] = eval_obj.id if eval_obj else None
        ai_avg = eval_obj.ai_average if eval_obj and eval_obj.status == Evaluation.Status.COMPLETED else None
        data["last_average"] = ai_avg
        data["status"] = DashboardService._determine_status(eval_obj, rag_date)
        data["keywords"] = eval_obj.module_keywords if eval_obj else []
        return data


class EvaluationHistorySerializer(serializers.ModelSerializer):
    """Serializer to represent the evaluation history for a module."""

    course_link = serializers.URLField(write_only=True)
    user = serializers.EmailField(source='triggered_by.email', read_only=True, default="System")
    date = serializers.CharField(source='formatted_date', read_only=True)

    class Meta:
        model = Evaluation
        fields = ['id', 'date', 'user', 'course_link']


class ScanOverviewSerializer(serializers.Serializer):
    """Serializer to represent the overview of scans for a specific evaluation."""

    name = serializers.CharField()
    id = serializers.IntegerField(allow_null=True)
    evaluable = serializers.BooleanField()
    scan_max = serializers.FloatField()
    scan_average = serializers.FloatField(allow_null=True)
    status = serializers.CharField()
    outdated = serializers.BooleanField()


class LinkModuleSerializer(serializers.Serializer):
    """Serializer to retrieve course link with id."""

    course_link = serializers.CharField()


class BasicInfoSerializer(serializers.Serializer):
    """Serializer to retrieve basic information about an evaluation."""

    elh = serializers.CharField()
    eqf = serializers.CharField()
    smcts = serializers.CharField()
    title = serializers.CharField()
    abstract = serializers.CharField()
    keywords = serializers.ListField(child=serializers.CharField())
    teachers = serializers.ListField(child=serializers.CharField())
    suggested_knowledge = serializers.CharField()
    suggested_skills = serializers.CharField()
    suggested_ra = serializers.CharField()

    def to_representation(self, obj):
        meta = obj.metadata_json or {}
        return {
            "elh": meta.get("elh", "N/A"),
            "eqf": meta.get("eqf", "N/A"),
            "smcts": meta.get("smcts", "N/A"),
            "title": meta.get("title") or obj.title or (obj.module.title if obj.module else "Untitled Module"),
            "abstract": meta.get("abstract", "No abstract available."),
            "keywords": obj.module_keywords,
            "teachers": obj.module_teachers,
            "suggested_knowledge": meta.get("suggested_knowledge", "N/A"),
            "suggested_skills": meta.get("suggested_skills", "N/A"),
            "suggested_ra": meta.get("suggested_ra", "N/A"),
        }
