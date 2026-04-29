# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path
from .views import assessment_views, evaluation_views, overview_views, reports_views


urlpatterns = [
    # EVALUATION LIFECYCLE
    path('evaluate/', evaluation_views.StartEvaluationView.as_view(), name='start_evaluation'),
    path('evaluation_status/module/<int:pk>/', evaluation_views.EvaluationStatusView.as_view(), name='evaluation_status_module'),
    path('evaluation_status/scan/<int:pk>/', evaluation_views.ScanStatusView.as_view(), name='evaluation_status_scan'),
    path('callback/', evaluation_views.EvaluationCallbackView.as_view(), name='evaluation_callback'),

    # RESULTS
    path('evaluation_detail/module/<int:pk>/', assessment_views.ResultDetailView.as_view(), {'model_type': 'module'}, name='evaluation_detail_module'),
    path('evaluation_detail/scan/<int:pk>/', assessment_views.ResultDetailView.as_view(), {'model_type': 'scan'}, name='evaluation_detail_scan'),

    # DASHBOARD & LISTS
    path('modules/', overview_views.DashboardListView.as_view(), name='get_user_modules'),
    path('list_evaluations/', overview_views.EvaluationHistoryListView.as_view(), name='list_evaluations'),
    path('evaluation_ids/<int:pk>/', overview_views.EvaluationStatusByIdView.as_view(), name='get_evaluation_ids'),
    path('link_module/<int:pk>/', overview_views.LinkModuleView.as_view(), name='get_module_link'),
    path('basic_information/<int:pk>/', overview_views.EvaluationBasicInfoView.as_view(), name='get_evaluation_basic_info'),

    # REPORTS
    path('download_pdf/<int:pk>/', reports_views.ReportDownloadView.as_view(), name='download_evaluation_pdf'),
]
