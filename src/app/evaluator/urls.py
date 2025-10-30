from django.urls import path
from .views import evaluate_module

urlpatterns = [
    path('evaluate/', evaluate_module),
]
