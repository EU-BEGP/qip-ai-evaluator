from django.urls import path
from .views import LoginProxyView

urlpatterns = [
    path('auth/login/', LoginProxyView.as_view(), name='login_proxy'),
]
