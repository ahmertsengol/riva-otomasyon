from django.urls import path

from . import views

app_name = "appointments"

urlpatterns = [
    # Hızlı kabul (walk-in)
    path("hasta-kabul/hizli/", views.quick_intake, name="walk_in"),
    # Takvim & randevular
    path("randevular/", views.calendar, name="calendar"),
    path("randevular/olaylar/", views.events, name="events"),
    path("randevular/tasi/", views.reschedule, name="reschedule"),
    path("randevular/yeni/", views.AppointmentCreateView.as_view(), name="create"),
    path("randevular/<int:pk>/", views.AppointmentDetailView.as_view(), name="detail"),
    path("randevular/<int:pk>/duzenle/", views.AppointmentUpdateView.as_view(), name="update"),
    path("randevular/<int:pk>/sil/", views.AppointmentDeleteView.as_view(), name="delete"),
    path("randevular/<int:pk>/durum/", views.set_status, name="set_status"),
    path("randevular/<int:pk>/muayeneye-al/", views.start_exam, name="start_exam"),
    # Randevu talepleri
    path("randevu-talepleri/", views.request_list, name="request_list"),
    path("randevu-talepleri/<int:pk>/yoksay/", views.request_dismiss, name="request_dismiss"),
    # Public API (landing page — sonra bağlanacak)
    path("api/appointment-requests/", views.api_create_request, name="api_create_request"),
]
