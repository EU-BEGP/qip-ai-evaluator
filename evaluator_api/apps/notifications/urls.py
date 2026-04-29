# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.urls import path

from . import views


urlpatterns = [
    path('user_mailbox/', views.UserMailboxView.as_view(), name='get_user_mailbox'),
    path('read_message/', views.MessageMarkReadView.as_view(), name='mark_message_read'),
    path('notifications_unread/', views.NotificationsUnreadCountView.as_view(), name='get_unread_notifications_count'),
]
