from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("giris/", views.RivaLoginView.as_view(), name="login"),
    path("cikis/", views.logout_view, name="logout"),
    path("sifre-sifirla/", views.password_reset_request, name="password_reset"),
    path("sifre-sifirla/dogrula/", views.password_reset_verify, name="password_reset_verify"),
    path("sifre-sifirla/yeni/", views.password_reset_set, name="password_reset_set"),
]
