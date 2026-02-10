# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path
from . import views

urlpatterns = [
    # Core
    path('evaluate/', views.start_evaluation, name='start_evaluation'),
    path('scans/criterions/<int:criterion_id>/ai-suggestion/', views.get_criterion_ai_suggestion, name='get_criterion_ai_suggestion'),
    path('verify_metadata/', views.validate_module_metadata, name='validate_module_metadata'),
    path('create_evaluation/', views.create_evaluation, name='create_evaluation'),
    
    # Lists & Dashboard
    path('list_evaluations/', views.list_evaluations, name='list_evaluations'),
    path('modules/<str:email>/', views.get_user_modules, name='get_user_modules'),
    
    # Status & Details
    path('evaluation_ids/<int:pk>/', views.get_evaluation_ids, name='get_evaluation_ids'),
    path('link_module/<int:pk>/', views.get_module_link, name='get_module_link'),
    path('evaluation_status/module/<int:pk>/', views.evaluation_status_module, name='evaluation_status_module'),
    path('evaluation_status/scan/<int:pk>/', views.evaluation_status_scan, name='evaluation_status_scan'),
    path('scans/', views.get_scans, name='get_rubric_scans'),
    path('scans/<int:module_id>/', views.get_scans, name='get_module_scans'),
    path('scans/criterions/<int:criterion_id>/result/', views.get_criterion_result, name='get_criterion_result'),
    
    # Results JSON
    path('evaluation_detail/module/<int:pk>/', views.evaluation_detail_module, name='evaluation_detail_module'),
    path('evaluation_detail/scan/<int:pk>/', views.evaluation_detail_scan, name='evaluation_detail_scan'),
    
    # Reports
    path('download_pdf/<int:pk>/', views.download_evaluation_pdf, name='download_evaluation_pdf'),
    path('basic_information/<int:evaluation_id>/', views.get_evaluation_basic_info, name='get_evaluation_basic_info'),
    
    # Webhook
    path('callback/', views.evaluation_callback, name='evaluation_callback'),

    # Criterion
    path('scans/<int:scan_id>/criterions/', views.get_scan_criterions, name='get_scan_criterions'),
    path('scans/criterions/<int:criterion_id>/', views.update_criterion_selection, name='update_criterion_selection'),
]
