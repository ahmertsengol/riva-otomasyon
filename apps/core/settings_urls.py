from django.urls import path

from . import settings_views as views

app_name = "settings"

urlpatterns = [
    path("", views.settings_index, name="index"),
    path("turler/", views.species_manage, name="species"),
    path("turler/<int:pk>/durum/", views.species_toggle, name="species_toggle"),
    path("denetim/", views.audit_log, name="audit_log"),
]
