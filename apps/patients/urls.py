from django.urls import path

from . import views

app_name = "patients"

urlpatterns = [
    path("", views.PatientListView.as_view(), name="list"),
    path("yeni/", views.PatientCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PatientDetailView.as_view(), name="detail"),
    path("<int:pk>/duzenle/", views.PatientUpdateView.as_view(), name="update"),
    path("<int:pk>/sil/", views.PatientDeleteView.as_view(), name="delete"),
]
