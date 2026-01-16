# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path
from .views import LoginProxyView

urlpatterns = [
    path('auth/login/', LoginProxyView.as_view(), name='login_proxy'),
]
