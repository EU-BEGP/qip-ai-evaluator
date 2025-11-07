from django.urls import path
from .views import evaluate_module, list_evaluations, get_evaluation_detail

urlpatterns = [
    # POST /api/evaluate/
    path('evaluate/', evaluate_module, name='evaluate_module'),
    
    # GET /api/module/<course_key>/evaluations/
    path('module/<str:course_key>/evaluations/', list_evaluations, name='list_evaluations'),
    
    # GET /api/evaluation/<id>/
    path('evaluation/<int:pk>/', get_evaluation_detail, name='get_evaluation_detail'),
]
