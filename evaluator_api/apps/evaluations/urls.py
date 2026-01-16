# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path
from . import views

urlpatterns = [
    # Core
    path('evaluate/', views.start_evaluation, name='start_evaluation'),
    
    # Lists & Dashboard
    path('list_evaluations/', views.list_evaluations, name='list_evaluations'),
    path('modules/<str:email>/', views.get_user_modules, name='get_user_modules'),
    
    # Status & Details
    path('evaluation_ids/<int:pk>/', views.get_evaluation_ids, name='get_evaluation_ids'),
    path('link_module/<int:pk>/', views.get_module_link, name='get_module_link'),
    path('evaluation_status/module/<int:pk>/', views.evaluation_status_module, name='evaluation_status_module'),
    path('evaluation_status/scan/<int:pk>/', views.evaluation_status_scan, name='evaluation_status_scan'),
    
    # Results JSON
    path('evaluation_detail/module/<int:pk>/', views.evaluation_detail_module, name='evaluation_detail_module'),
    path('evaluation_detail/scan/<int:pk>/', views.evaluation_detail_scan, name='evaluation_detail_scan'),
    
    # Reports
    path('download_pdf/<int:pk>/', views.download_evaluation_pdf, name='download_evaluation_pdf'),
    
    # Webhook
    path('callback/', views.evaluation_callback, name='evaluation_callback'),
]
