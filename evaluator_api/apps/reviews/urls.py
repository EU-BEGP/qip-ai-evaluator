from django.urls import path
from . import views

urlpatterns = [
    path('request_peer_reviews/', views.request_peer_reviews, name='request_peer_reviews'),
    path('reviews/<int:evaluation_id>/', views.get_evaluation_reviews, name='get_evaluation_reviews'),
    path('scans_info/<int:review_id>/', views.get_review_scans_info, name='get_review_scans_info'),
    path('review_detail/<int:review_id>/<int:scan_id>/', views.get_review_details, name='get_review_details'),
    path('details/', views.get_external_review_details, name='get_external_review_details'),
    path('criterion/<int:criterion_id>/', views.update_criterion_feedback, name='update_criterion_feedback'),
    path('submit/', views.submit_review, name='submit_review'),
    path('completion_status/', views.get_review_completion_status, name='get_review_completion_status'),
]
