# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path
from .views import evaluate_module, module_last_modified, get_module_metadata

urlpatterns = [
    # POST /api/evaluate/
    path('evaluate/', evaluate_module, name='evaluate_module'),
    path('module_last_modified/', module_last_modified, name='module_last_modified'),
    path('extract_metadata/', get_module_metadata, name='extract_metadata'),
]
