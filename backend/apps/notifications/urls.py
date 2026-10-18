from django.urls import path

from . import views

urlpatterns = [
    path("me/notifications", views.NotificationsView.as_view(), name="me-notifications"),
    path("me/notifications/unread", views.UnreadView.as_view(), name="me-notifications-unread"),
    path("me/notifications/read", views.MarkReadView.as_view(), name="me-notifications-read"),
]
