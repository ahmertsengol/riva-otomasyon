from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import PatientForm
from .models import Patient


class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = "patients/list.html"
    context_object_name = "patients"
    paginate_by = 25

    def get_queryset(self):
        qs = Patient.objects.select_related("owner", "species").order_by("name")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(microchip_no__icontains=q)
                | Q(owner__first_name__icontains=q)
                | Q(owner__last_name__icontains=q)
                | Q(owner__phone__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class PatientDetailView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = "patients/detail.html"
    context_object_name = "patient"

    def get_queryset(self):
        return Patient.objects.select_related("owner", "species")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tab_list"] = [
            ("genel", "Genel"),
            ("timeline", "Zaman Çizelgesi"),
            ("randevular", "Randevular"),
            ("asilar", "Aşılar"),
            ("muayeneler", "Muayeneler"),
            ("operasyonlar", "Operasyonlar"),
            ("lab", "Lab"),
            ("notlar", "Notlar"),
            ("dosyalar", "Dosyalar"),
        ]
        try:
            from apps.appointments.models import Appointment

            ctx["appointments"] = (
                Appointment.objects.filter(patient=self.object)
                .select_related("owner", "assigned_vet")
                .order_by("-starts_at")
            )
        except Exception:
            ctx["appointments"] = []
        try:
            from apps.medical.models import Examination

            ctx["examinations"] = (
                Examination.objects.filter(patient=self.object)
                .select_related("vet", "appointment")
                .order_by("-created_at")
            )
        except Exception:
            ctx["examinations"] = []
        try:
            from apps.medical.models import LabResult, Note, Operation

            ctx["operations"] = (
                Operation.objects.filter(patient=self.object).select_related("vet").order_by("-date")
            )
            ctx["lab_results"] = (
                LabResult.objects.filter(patient=self.object)
                .select_related("examination")
                .order_by("-date", "-created_at")
            )
            ctx["medical_notes"] = Note.objects.filter(patient=self.object).order_by("-created_at")
        except Exception:
            ctx["operations"] = []
            ctx["lab_results"] = []
            ctx["medical_notes"] = []
        try:
            from apps.vaccines.models import VaccineRecord

            ctx["vaccine_records"] = (
                VaccineRecord.objects.filter(patient=self.object)
                .select_related("vaccine_definition", "vet")
                .order_by("-applied_at", "-created_at")
            )
        except Exception:
            ctx["vaccine_records"] = []
        # Zaman çizelgesi ve tıbbi kayıtlar ilgili modüller geldikçe doldurulur.
        try:
            from apps.medical.services import patient_timeline

            ctx["timeline"] = patient_timeline(self.object)
        except Exception:
            ctx["timeline"] = []
        return ctx


class PatientCreateView(LoginRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = "patients/form.html"

    def get_initial(self):
        initial = super().get_initial()
        owner_id = self.request.GET.get("owner")
        if owner_id:
            initial["owner"] = owner_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Hayvan kaydı oluşturuldu.")
        return super().form_valid(form)


class PatientUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = "patients/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Hayvan kaydı güncellendi.")
        return super().form_valid(form)


class PatientDeleteView(LoginRequiredMixin, DeleteView):
    model = Patient
    template_name = "patients/confirm_delete.html"
    success_url = reverse_lazy("patients:list")

    def form_valid(self, form):
        messages.success(self.request, "Hayvan kaydı silindi.")
        return super().form_valid(form)
