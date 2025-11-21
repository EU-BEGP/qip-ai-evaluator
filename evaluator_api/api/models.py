import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# --- 1. Custom User Manager ---
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

# --- 2. Custom User Model (User) ---
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

# --- 3. Module Model ---
class Module(models.Model):
    user = models.ForeignKey('api.User', on_delete=models.CASCADE, related_name="modules")
    course_key = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        unique_together = ('user', 'course_key') 
    def __str__(self):
        return self.course_key

# --- 4. Evaluation Model ---
class Evaluation(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'Not Started', 'Not Started'
        IN_PROGRESS = 'In Progress', 'In Progress'
        COMPLETED = 'Completed', 'Completed'
        FAILED = 'Failed', 'Failed'

    id = models.AutoField(primary_key=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="evaluations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    
    # This stores the RAG API's 'last_modified_date' as the version
    created_at = models.DateTimeField() 
    
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Stores the list of scans requested, e.g., ["Summary Scan"]
    requested_scans = models.JSONField(default=list)
    
    # Stores the final *merged* JSON file
    result_json = models.JSONField(null=True, blank=True)

    title = models.CharField(max_length=255, blank=True, null=True)

    document_snapshot = models.TextField(null=True, blank=True)

    @property
    def formatted_date(self):
        return self.created_at.strftime("%Y-%m-%d %H:%M") 
    def __str__(self):
        return f"Evaluation {self.id} for {self.module.course_key}"

# --- 5. Scan Model ---
class Scan(models.Model):
    class ScanType(models.TextChoices):
        ACADEMIC_METADATA = 'Academic Metadata Scan', 'Academic Metadata Scan'
        LEARNING_CONTENT = 'Learning Content Scan', 'Learning Content Scan'
        ASSESSMENT = 'Assessment Scan', 'Assessment Scan'
        MULTIMEDIA = 'Multimedia Scan', 'Multimedia Scan'
        CERTIFICATE = 'Certificate Scan', 'Certificate Scan'
        SUMMARY = 'Summary Scan', 'Summary Scan'
        
    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        IN_PROGRESS = 'In Progress', 'In Progress'
        COMPLETED = 'Completed', 'Completed'
        FAILED = 'Failed', 'Failed'
        
    id = models.AutoField(primary_key=True)
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scans")
    scan_type = models.CharField(max_length=100, choices=ScanType.choices)
    
    # Default changed to IN_PROGRESS to match new view logic
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    
    # Stores the *partial* JSON for this scan only
    result_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.scan_type
    
# --- 6. Message Model (New) ---
class Message(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    # 'read' maps to 'read' in JSON, avoid conflict with read() method
    is_read = models.BooleanField(default=False) 
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Sort by newest first
        ordering = ['-created_at']

    def __str__(self):
        return f"Message {self.id} for {self.user.email}"
