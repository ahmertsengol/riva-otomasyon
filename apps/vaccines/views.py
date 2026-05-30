from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.models import User
from apps.core.models import ClinicSettings
from apps.core.pdf import render_pdf_response
from apps.patients.models import Patient

from .forms import VaccineDefinitionForm, VaccineRecordForm
from .models import VaccineDefinition, VaccineRecord


class VaccineRecordCreateView(LoginRequiredMixin, CreateView):
    model = VaccineRecord
    form_class = VaccineRecordForm
    template_name = "vaccines/record_form.html"

    def get_initial(self):
        initial = super().get_initial()
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
        initial.setdefault("applied_at", timezone.localdate())
        user = self.request.user
        if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in {
            User.Role.VET,
            User.Role.ADMIN,
        }:
            initial.setdefault("vet", user.pk)
        return initial

    def form_valid(self, form):
        if not form.instance.vet_id and self.request.user.is_authenticated:
            form.instance.vet = self.request.user
        messages.success(self.request, "Aşı kaydı oluşturuldu.")
        return super().form_valid(form)


class VaccineRecordDetailView(LoginRequiredMixin, DetailView):
    model = VaccineRecord
    template_name = "vaccines/record_detail.html"
    context_object_name = "record"

    def get_queryset(self):
        return VaccineRecord.objects.select_related(
            "patient", "patient__owner", "patient__species", "vaccine_definition", "vet"
        )


class UpcomingVaccineListView(LoginRequiredMixin, ListView):
    model = VaccineRecord
    template_name = "vaccines/due_list.html"
    context_object_name = "records"

    def get_queryset(self):
        today = timezone.localdate()
        return (
            VaccineRecord.objects.select_related(
                "patient", "patient__owner", "patient__species", "vaccine_definition", "vet"
            )
            .filter(next_due_at__gte=today, next_due_at__lte=today + timedelta(days=30))
            .order_by("next_due_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Yaklaşan Aşılar"
        ctx["empty_text"] = "Önümüzdeki 30 gün içinde yaklaşan aşı yok."
        ctx["tone"] = "warning"
        return ctx


class OverdueVaccineListView(LoginRequiredMixin, ListView):
    model = VaccineRecord
    template_name = "vaccines/due_list.html"
    context_object_name = "records"

    def get_queryset(self):
        return (
            VaccineRecord.objects.select_related(
                "patient", "patient__owner", "patient__species", "vaccine_definition", "vet"
            )
            .filter(next_due_at__lt=timezone.localdate())
            .order_by("next_due_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Geciken Aşılar"
        ctx["empty_text"] = "Geciken aşı yok."
        ctx["tone"] = "danger"
        return ctx


class VaccineProtocolListView(LoginRequiredMixin, ListView):
    model = VaccineDefinition
    template_name = "vaccines/protocols.html"
    context_object_name = "protocols"

    def get_queryset(self):
        return VaccineDefinition.objects.select_related("species").order_by("species__name", "name")


class VaccineProtocolCreateView(LoginRequiredMixin, CreateView):
    model = VaccineDefinition
    form_class = VaccineDefinitionForm
    template_name = "vaccines/protocol_form.html"
    success_url = reverse_lazy("vaccines:protocols")

    def form_valid(self, form):
        messages.success(self.request, "Aşı protokolü oluşturuldu.")
        return super().form_valid(form)


class VaccineProtocolUpdateView(LoginRequiredMixin, UpdateView):
    model = VaccineDefinition
    form_class = VaccineDefinitionForm
    template_name = "vaccines/protocol_form.html"
    success_url = reverse_lazy("vaccines:protocols")

    def form_valid(self, form):
        messages.success(self.request, "Aşı protokolü güncellendi.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# PDF çıktıları — aşı kartı (sertifika) ve aşı geçmişi
# ---------------------------------------------------------------------------
@login_required
def vaccine_certificate_pdf(request, pk):
    """Tek aşı kaydı için aşı kartı / sertifika."""
    record = get_object_or_404(
        VaccineRecord.objects.select_related(
            "patient", "patient__owner", "patient__species", "vaccine_definition", "vet"
        ),
        pk=pk,
    )
    return render_pdf_response(
        "vaccines/certificate_pdf.html",
        {"record": record, "clinic": ClinicSettings.load()},
        request,
        filename=f"asi-karti-{record.pk}.pdf",
    )


@login_required
def vaccine_history_pdf(request, patient_id):
    """Hayvanın tüm aşı geçmişi (uygulanan + planlanan)."""
    patient = get_object_or_404(
        Patient.objects.select_related("owner", "species"), pk=patient_id
    )
    records = (
        VaccineRecord.objects.filter(patient=patient)
        .select_related("vaccine_definition", "vet")
        .order_by("-applied_at", "-created_at")
    )
    return render_pdf_response(
        "vaccines/history_pdf.html",
        {"patient": patient, "records": records, "clinic": ClinicSettings.load()},
        request,
        filename=f"asi-gecmisi-{patient.pk}.pdf",
    )
