from django.urls import path

from . import views

app_name = "medical"

urlpatterns = [
    path("muayeneler/", views.ExaminationListView.as_view(), name="examination_list"),
    path("muayeneler/yeni/", views.ExaminationCreateView.as_view(), name="examination_create"),
    path("muayeneler/<int:pk>/", views.ExaminationDetailView.as_view(), name="examination_detail"),
    path("muayene-secenekleri/", views.examination_options, name="examination_options"),
    path("receteler/yeni/", views.PrescriptionCreateView.as_view(), name="prescription_create"),
    path("receteler/<int:pk>/", views.PrescriptionDetailView.as_view(), name="prescription_detail"),
    path("receteler/<int:pk>/pdf/", views.prescription_pdf, name="prescription_pdf"),
    path("operasyonlar/yeni/", views.OperationCreateView.as_view(), name="operation_create"),
    path("operasyonlar/<int:pk>/", views.OperationDetailView.as_view(), name="operation_detail"),
    path("lab/yeni/", views.LabResultCreateView.as_view(), name="lab_result_create"),
    path("lab/<int:pk>/", views.LabResultDetailView.as_view(), name="lab_result_detail"),
    path("notlar/yeni/", views.NoteCreateView.as_view(), name="note_create"),
    path("notlar/<int:pk>/", views.NoteDetailView.as_view(), name="note_detail"),
]
