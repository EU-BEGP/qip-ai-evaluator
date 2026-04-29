# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import hashlib
import json

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class Rubric(models.Model):
    """Represents the rubric that contains scans and criteria (based on JSON)."""

    created_at = models.DateTimeField(auto_now_add=True)
    content = models.JSONField()
    content_hash = models.CharField(max_length=64, unique=True, editable=False, blank=True)
    rubric_map = models.JSONField(editable=False, default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_active(self):
        latest = Rubric.objects.first()
        return self == latest
    
    @property
    def available_scans(self):
        if isinstance(self.content, list):
            return [scan.get("scan") for scan in self.content if isinstance(scan, dict) and scan.get("scan")]
        return []

    def get_criteria_names(self, scan_type):
        return list(self.rubric_map.get(scan_type, {}).keys())

    def get_criterion(self, scan_type, criterion_name):
        return self.rubric_map.get(scan_type, {}).get(criterion_name)
    
    def build_map(self):
        data = self.content or []
        if not isinstance(data, list):
            return {}

        result = {}
        for scan in data:
            if not isinstance(scan, dict):
                continue

            scan_name = scan.get("scan")
            if not scan_name:
                continue

            criteria = scan.get("criteria", [])
            criteria_map = {}
            for criterion in criteria:
                if not isinstance(criterion, dict):
                    continue

                name = criterion.get("name")
                if not name:
                    continue

                criteria_map[name] = criterion

            result[scan_name] = criteria_map

        return result
    
    def save(self, *args, **kwargs):
        if self.content and not self.content_hash:
            normalized = json.dumps(self.content, sort_keys=True, separators=(",", ":"))
            self.content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            self.rubric_map = self.build_map()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Rubric {self.id} ({self.created_at.strftime('%Y-%m-%d')})"


class Module(models.Model):
    """Represents a unique learning resource (URL) shared across the platform."""

    course_key = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course_key"]

    def __str__(self):
        return self.title or self.course_key


class UserModule(models.Model):
    """Links a User to a Module, creating their personal dashboard view."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_modules")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="followed_by")
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "module"], name="unique_user_module")
        ]
        ordering = ["-last_accessed"]

    def __str__(self):
        return f"{self.user_id} - {self.module_id}"


class Evaluation(models.Model):
    """Represents a specific assessment of a Module."""

    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not Started'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        INCOMPLETED = 'INCOMPLETED', 'Incompleted'
        FAILED = 'FAILED', 'Failed'

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="evaluations")
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="triggered_evaluations")
    rubric = models.ForeignKey(Rubric, on_delete=models.PROTECT, null=True, blank=True, related_name="evaluations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    requested_scans = models.JSONField(default=list, blank=True)
    result_json = models.JSONField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    document_snapshot = models.TextField(blank=True)
    metadata_json = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["module", "-created_at"]),
        ]
    
    @property
    def formatted_date(self):
        return self.created_at.strftime("%Y-%m-%d %H:%M") 
    
    @property
    def ai_average(self):
        if not self.result_json:
            return None
        
        total_score, count = 0.0, 0
        for item in self.result_json.get("content", []):
            for criterion in item.get("criteria", []):
                try:
                    score = criterion.get("score")
                    if score is not None:
                        total_score += float(score)
                        count += 1
                except (ValueError, TypeError):
                    continue
        return round(total_score / count, 2) if count > 0 else None

    @property
    def module_keywords(self):
        if not self.metadata_json: 
            return []
        raw = self.metadata_json.get('keywords', [])
        if isinstance(raw, str):
            return [k.strip() for k in raw.split(',') if k]
        return raw if isinstance(raw, list) else []

    @property
    def module_teachers(self):
        if not self.metadata_json: 
            return []
        raw = self.metadata_json.get('teachers', [])
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str) and raw != "No teachers information available.":
            return [t.strip() for t in raw.split(',') if t.strip()]
        return []

    def __str__(self):
        return f"Eval {self.id} · {self.module.course_key} · {self.status}"


class Scan(models.Model):
    """Represents a specific functional area (criterion) within an Evaluation."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scans")
    scan_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    result_json = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["evaluation", "scan_type"], name="unique_scan_per_evaluation")
        ]
        ordering = ['id']

    @property
    def is_evaluable_individual(self):
        return self.status not in {self.Status.IN_PROGRESS, self.Status.COMPLETED}
    
    @property
    def scan_average(self):
        if not self.result_json: return None
        total, count = 0.0, 0
        for item in self.result_json.get("content", []):
            for crit in item.get("criteria", []):
                try:
                    total += float(crit.get("score", 0))
                    count += 1
                except (ValueError, TypeError):
                    continue
        return round(total / count, 2) if count > 0 else None
    
    def clean(self):
        rubric = getattr(self.evaluation, "rubric", None)
        if rubric and self.scan_type not in rubric.available_scans:
            raise ValidationError(f"Invalid scan type: {self.scan_type}")
    
    def __str__(self):
        return f"{self.scan_type} · Eval {self.evaluation_id} · {self.get_status_display()}"
