from django.urls import path

from . import views

app_name = "owners"

urlpatterns = [
    path("", views.OwnerListView.as_view(), name="list"),
    path("secenekler/", views.owner_options, name="options"),
    path("yeni/", views.OwnerCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OwnerDetailView.as_view(), name="detail"),
    path("<int:pk>/duzenle/", views.OwnerUpdateView.as_view(), name="update"),
    path("<int:pk>/sil/", views.OwnerDeleteView.as_view(), name="delete"),
]
