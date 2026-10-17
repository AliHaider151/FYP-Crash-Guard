from django.urls import include, path


urlpatterns = [path("", include("app.web.urls"))]
