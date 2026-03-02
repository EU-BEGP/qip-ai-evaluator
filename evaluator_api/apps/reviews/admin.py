from django.contrib import admin
from .models import ExternalReview, CriterionFeedback

@admin.register(ExternalReview)
class ExternalReviewAdmin(admin.ModelAdmin):
    # Admin for external review invitations
    list_display = ('id', 'reviewer_email', 'evaluation', 'is_completed', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reviewer_email', 'evaluation__module__course_key')
    readonly_fields = ('token', 'created_at', 'completed_at')

@admin.register(CriterionFeedback)
class CriterionFeedbackAdmin(admin.ModelAdmin):
    # Admin for individual criterion feedbacks
    list_display = ('id', 'review', 'criterion', 'score')
    list_filter = ('score',)
    search_fields = ('review__reviewer_email', 'criterion__criterion_name')
