# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path

from .views import (
    EvaluateModuleView,
    ModuleLastModifiedView,
    ModuleMetadataView,
)

urlpatterns = [
    path("evaluate/", EvaluateModuleView.as_view(), name="evaluate_module"),
    path("module_last_modified/", ModuleLastModifiedView.as_view(), name="module_last_modified"),
    path("extract_metadata/", ModuleMetadataView.as_view(), name="extract_metadata"),
]
