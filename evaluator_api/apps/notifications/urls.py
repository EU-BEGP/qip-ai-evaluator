from django.urls import path
from . import views

urlpatterns = [
    path('user_mailbox/<str:email>/', views.get_user_mailbox, name='get_user_mailbox'),
    path('read_message/', views.mark_message_read, name='mark_message_read'),
    path('notifications_unread/<str:email>/', views.get_unread_notifications_count, name='get_unread_notifications_count'),
]
