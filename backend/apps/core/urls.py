from django.urls import path

from .views import HealthView, JobView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("jobs/<str:job_id>", JobView.as_view(), name="job"),
]
