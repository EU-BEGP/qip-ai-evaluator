# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

class Rubric(models.Model):
    # Represents the rubric that contains scans and criteria (based on JSON)
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.JSONField()

    class Meta:
        ordering = ['-created_at']

    @property
    def is_active(self):
        latest = Rubric.objects.first()
        return latest and self.id == latest.id
    
    @property
    def available_scans(self):
        data = self.content or {}
        if isinstance(data, list):
            return [item.get('scan') for item in data if isinstance(item, dict) and 'scan' in item]
        elif isinstance(data, dict):
            return list(data.get('scans', {}).keys())
        return []

    @property
    def get_criteria_names(self, scan_name):
        data = self.content or {}
        scan_config = []

        if isinstance(data, list):
            found = next((i for i in data if i.get('scan') == scan_name), None)
            if found: scan_config = found.get('criteria', [])
        elif isinstance(data, dict):
            scan_config = data.get('scans', {}).get(scan_name, {}).get('criteria', [])
            
        return [c.get('name') for c in scan_config if isinstance(c, dict)]

    def __str__(self):
        return f"Rubric {self.id} ({self.created_at.strftime('%Y-%m-%d')})"

class Module(models.Model):
    # Represents a unique learning resource (URL) shared across the platform
    course_key = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.course_key

class UserModule(models.Model):
    # Links a User to a Module, creating their personal dashboard view
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_modules")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="followed_by")
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'module')
        ordering = ['-last_accessed']

class Evaluation(models.Model):
    # Represents a specific assessment of a Module
    class Status(models.TextChoices):
        NOT_STARTED = 'Not Started', 'Not Started'
        IN_PROGRESS = 'In Progress', 'In Progress'
        COMPLETED = 'Completed', 'Completed'
        INCOMPLETED = 'Incompleted', 'Incompleted'
        SELF_ASSESSMENT = 'SELF_ASSESSMENT', 'Self Assessment'

    id = models.AutoField(primary_key=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="evaluations")
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="triggered_evaluations")
    
    # Link to the specific Rubric version used for this evaluation
    rubric = models.ForeignKey(Rubric, on_delete=models.PROTECT, null=True, related_name="evaluations")
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SELF_ASSESSMENT)
    created_at = models.DateTimeField() 
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)
    requested_scans = models.JSONField(default=list)
    result_json = models.JSONField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    document_snapshot = models.TextField(null=True, blank=True)
    metadata_json = models.JSONField(null=True, blank=True)
    module_last_modified = models.DateTimeField(null=True, blank=True)

    @property
    def formatted_date(self):
        return self.created_at.strftime("%Y-%m-%d %H:%M") 
    
    @property
    def is_runnable(self):
        latest = self.module.evaluations.order_by('-created_at').first()
        if latest and latest.id != self.id:
            return False

        if self.status in [self.Status.NOT_STARTED, self.Status.FAILED]:
            return True
            
        if self.status == self.Status.COMPLETED:
            return False
            
        if self.status == self.Status.IN_PROGRESS:
            return False
            
        if self.status == self.Status.INCOMPLETED:
            return True

        return True

    def __str__(self):
        return f"Evaluation {self.id} for {self.module.course_key}"

class Scan(models.Model):
    # Represents a specific functional area (criterion) within an Evaluation
    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        IN_PROGRESS = 'In Progress', 'In Progress'
        COMPLETED = 'Completed', 'Completed'
        FAILED = 'Failed', 'Failed'
        
    id = models.AutoField(primary_key=True)
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scans")
    scan_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    result_json = models.JSONField(null=True, blank=True)

    def clean(self):
        if self.evaluation and self.evaluation.rubric:
            valid_types = self.evaluation.rubric.available_scans
            if self.scan_type not in valid_types:
                raise ValidationError(f"Invalid scan type: {self.scan_type}")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def is_evaluable_individual(self):
        if self.status == self.Status.FAILED:
            return True
        if self.status in [self.Status.IN_PROGRESS, self.Status.COMPLETED]:
            return False
        return True

    def __str__(self):
        return self.scan_type

class Criterion(models.Model):
    # Represents specific granular results within a Scan
    id = models.AutoField(primary_key=True)
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="criteria_results")
    criterion_name = models.CharField(max_length=255)
    status = models.CharField(max_length=100, blank=True, null=True)
    result = models.TextField(blank=True, null=True)
    
    class Selection(models.TextChoices):
        YES = 'YES', 'Yes'
        NO = 'NO', 'No'
        NOT_APPLICABLE = 'NOT APPLICABLE', 'Not Applicable'
    
    user_selection = models.CharField(
        max_length=50, 
        choices=Selection.choices, 
        null=True, 
        blank=True
    )

    class Meta:
        unique_together = ('scan', 'criterion_name')

    def clean(self):
        if self.scan and self.scan.evaluation and self.scan.evaluation.rubric:
            valid_names = self.scan.evaluation.rubric.get_criteria_names(self.scan.scan_type)
            if self.criterion_name not in valid_names:
                raise ValidationError(f"Invalid criterion: {self.criterion_name}")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.criterion_name}: {self.status}"
