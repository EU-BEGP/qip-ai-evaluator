from django.db import models
from django.conf import settings
from django.utils import timezone

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
        FAILED = 'Failed', 'Failed'

    id = models.AutoField(primary_key=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="evaluations")
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="triggered_evaluations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    created_at = models.DateTimeField() 
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)
    requested_scans = models.JSONField(default=list)
    result_json = models.JSONField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    document_snapshot = models.TextField(null=True, blank=True)
    metadata_json = models.JSONField(null=True, blank=True)

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
    class ScanType(models.TextChoices):
        ACADEMIC_METADATA = 'Academic Metadata Scan', 'Academic Metadata Scan'
        LEARNING_CONTENT = 'Learning Content Scan', 'Learning Content Scan'
        ASSESSMENT = 'Assessment Scan', 'Assessment Scan'
        MULTIMEDIA = 'Multimedia Scan', 'Multimedia Scan'
        CERTIFICATE = 'Certificate Scan', 'Certificate Scan'
        SUMMARY = 'Summary Scan', 'Summary Scan'
        
    class Status(models.TextChoices):
        IN_PROGRESS = 'In Progress', 'In Progress'
        COMPLETED = 'Completed', 'Completed'
        FAILED = 'Failed', 'Failed'
        
    id = models.AutoField(primary_key=True)
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scans")
    scan_type = models.CharField(max_length=100, choices=ScanType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    result_json = models.JSONField(null=True, blank=True)

    @property
    def is_evaluable_individual(self):
        if self.status == self.Status.FAILED:
            return True
        if self.status in [self.Status.IN_PROGRESS, self.Status.COMPLETED]:
            return False
        return True

    def __str__(self):
        return self.scan_type
