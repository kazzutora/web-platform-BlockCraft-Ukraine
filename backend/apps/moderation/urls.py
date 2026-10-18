from django.urls import path

from . import views

urlpatterns = [path("reports", views.ReportsView.as_view(), name="reports")]
