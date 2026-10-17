from django.urls import path

from app.web import views


app_name = "web"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("detection/start/", views.start_detection, name="start_detection"),
    path("detection/stop/", views.stop_detection, name="stop_detection"),
    path("detection/status/", views.detection_status, name="detection_status"),
    path("detection/preview/", views.detection_preview, name="detection_preview"),
]
