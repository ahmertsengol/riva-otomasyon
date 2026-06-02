from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.index, name="index"),
    path("islem/yeni/", views.ChargeCreateView.as_view(), name="charge_create"),
    path("muayene/<int:exam_id>/hesap-kapat/", views.checkout, name="checkout"),
    path("islem/<int:pk>/", views.charge_detail, name="charge_detail"),
    path("islem/<int:pk>/e-fatura/", views.e_invoice_sim, name="e_invoice_sim"),
    path("islem/<int:charge_pk>/tahsilat/", views.payment_create, name="charge_payment"),
    path("tahsilat/yeni/", views.payment_create, name="payment_create"),
    path("hizmetler/", views.ServiceItemListView.as_view(), name="services"),
    path("hizmetler/yeni/", views.ServiceItemCreateView.as_view(), name="service_create"),
    path("hizmetler/<int:pk>/duzenle/", views.ServiceItemUpdateView.as_view(), name="service_update"),
]
