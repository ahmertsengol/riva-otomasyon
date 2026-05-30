from django.urls import path

from . import views

app_name = "vaccines"

urlpatterns = [
    path("", views.UpcomingVaccineListView.as_view(), name="index"),
    path("yaklasan/", views.UpcomingVaccineListView.as_view(), name="upcoming"),
    path("geciken/", views.OverdueVaccineListView.as_view(), name="overdue"),
    path("uygula/", views.VaccineRecordCreateView.as_view(), name="record_create"),
    path("kayit/<int:pk>/", views.VaccineRecordDetailView.as_view(), name="record_detail"),
    path("kayit/<int:pk>/sertifika/", views.vaccine_certificate_pdf, name="certificate_pdf"),
    path("gecmis/<int:patient_id>/pdf/", views.vaccine_history_pdf, name="history_pdf"),
    path("protokoller/", views.VaccineProtocolListView.as_view(), name="protocols"),
    path("protokoller/yeni/", views.VaccineProtocolCreateView.as_view(), name="protocol_create"),
    path("protokoller/<int:pk>/duzenle/", views.VaccineProtocolUpdateView.as_view(), name="protocol_update"),
]
