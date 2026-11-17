from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "MyFitnessPal · Administración"
admin.site.site_title = "MyFitnessPal"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("nutricion.urls")),
]
