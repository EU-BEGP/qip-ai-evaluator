from django.urls import path
from . import views

urlpatterns = [
    # --- Auth ---
    path('auth/login/', views.login_proxy, name='login_proxy'),

    # --- Endpoints ---
    path('evaluate/', views.start_new_evaluation, name='start_evaluation'),
    path('list_evaluations/', views.list_evaluations, name='list_evaluations'),
    path('evaluation_detail/module/<int:pk>/', views.evaluation_detail_module, name='evaluation_detail_module'),
    path('evaluation_detail/scan/<int:pk>/', views.evaluation_detail_scan, name='evaluation_detail_scan'),
    path('evaluation_status/module/<int:pk>/', views.evaluation_status_module, name='evaluation_status_module'),
    path('evaluation_status/scan/<int:pk>/', views.evaluation_status_scan, name='evaluation_status_scan'),

    # --- Internal Callback ---
    path('callback/', views.evaluation_callback, name='evaluation_callback'),
]
