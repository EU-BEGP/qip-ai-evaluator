# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from django.urls import path

from . import views


urlpatterns = [
    # Auth Endpoints
    path('auth/login/', views.Book4RLabLoginView.as_view(), name='book4rlab_login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # User Profile Endpoints
    path('me/', views.UserProfileMeView.as_view(), name='user_profile_me'),
    path('profile/<int:pk>/', views.UserProfileDetailView.as_view(), name='user_profile_detail'),
]
