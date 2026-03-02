import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.evaluations.models import Evaluation, Criterion
from django.utils import timezone

class ExternalReview(models.Model):
    # Represents the review session assigned to an external user via a token
    id = models.AutoField(primary_key=True)
    evaluation = models.ForeignKey(
        Evaluation, 
        on_delete=models.CASCADE, 
        related_name="external_reviews"
    )
    reviewer_email = models.EmailField()
    # The access key. Generated automatically when the record is created.
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        # Prevent sending two active invitations to the same email for the same module
        unique_together = ('evaluation', 'reviewer_email')

    def mark_as_completed(self):
        # Helper method to be called if the user submits the final review
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        status_str = "Completed" if self.is_completed else "Pending"
        return f"Review by {self.reviewer_email} ({status_str})"


class CriterionFeedback(models.Model):
    # Represents the individual vote (score and comment) of an external reviewer for a Criterion
    id = models.AutoField(primary_key=True)
    review = models.ForeignKey(
        ExternalReview, 
        on_delete=models.CASCADE, 
        related_name="feedbacks"
    )
    criterion = models.ForeignKey(
        Criterion, 
        on_delete=models.CASCADE, 
        related_name="external_feedbacks"
    )
    score = models.DecimalField(
        max_digits=3, 
        decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    comment = models.TextField(blank=True, null=True)

    class Meta:
        # A reviewer can only give one score to the same question
        unique_together = ('review', 'criterion')

    def __str__(self):
        return f"{self.score}/5.0 for Criterion ID: {self.criterion.id}"
