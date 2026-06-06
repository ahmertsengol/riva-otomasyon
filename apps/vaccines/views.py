from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
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
        if def_id := self.request.GET.get("definition"):
            initial["vaccine_definition"] = def_id
        initial.setdefault("applied_at", timezone.localdate())
        user = self.request.user
        if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in {
            User.Role.VET,
            User.Role.ADMIN,
        }:
            initial.setdefault("vet", user.pk)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        defs = VaccineDefinition.objects.filter(active=True).select_related("species")
        patient_id = self.request.GET.get("patient")
        if patient_id:
            patient = Patient.objects.filter(pk=patient_id).first()
            if patient:
                defs = defs.filter(species_id=patient.species_id)
        ctx["init_definitions"] = defs
        ctx["init_def_selected"] = self.request.GET.get("definition", "")
        return ctx

    def form_valid(self, form):
        if not form.instance.vet_id and self.request.user.is_authenticated:
            form.instance.vet = self.request.user
        response = super().form_valid(form)
        if form.cleaned_data.get("create_followup"):
            self._create_followup_appointment(self.object)
        # Bu kayıt bir protokol randevusundan açıldıysa o randevuyu tamamla
        # (POST gizli input öncelikli; query string her tarayıcıda korunmayabilir)
        if appt_id := (self.request.POST.get("appointment") or self.request.GET.get("appointment")):
            from apps.appointments.models import Appointment

            Appointment.objects.filter(pk=appt_id).update(
                status=Appointment.Status.COMPLETED
            )
        messages.success(self.request, f"{self.object.display_name} kaydı oluşturuldu.")
        return response

    def _create_followup_appointment(self, record):
        """Sonraki doz tarihine 'planlandı' (talep) randevu oluşturur (idempotent).

        Randevu, hangi protokol/doz olduğunu taşır → o gün takvimde/brifingde
        'Karma Aşı 2. doz · Boncuk' diye net görünür.
        """
        if not record.next_due_at:
            return
        from datetime import datetime, time

        from apps.appointments.models import Appointment

        definition = record.vaccine_definition
        appt_type = Appointment.CATEGORY_TO_TYPE.get(
            definition.category if definition else "", Appointment.Type.VACCINE
        )
        next_dose = record.next_dose_number
        starts_at = timezone.make_aware(datetime.combine(record.next_due_at, time(10, 0)))
        exists = Appointment.objects.filter(
            patient=record.patient,
            protocol_definition=definition,
            starts_at__date=record.next_due_at,
        ).exists()
        if exists:
            return
        Appointment.objects.create(
            owner=record.patient.owner,
            patient=record.patient,
            starts_at=starts_at,
            type=appt_type,
            status=Appointment.Status.REQUESTED,
            source=Appointment.Source.AUTO_FOLLOWUP,
            assigned_vet=record.vet,
            protocol_definition=definition,
            dose_number=next_dose,
            note=f"Otomatik: {record.display_name} {next_dose}. doz",
        )


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
        ctx["title"] = "Yaklaşan (Aşı / Parazit / İlaç)"
        ctx["empty_text"] = "Önümüzdeki 30 gün içinde yaklaşan uygulama yok."
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
        ctx["title"] = "Geciken (Aşı / Parazit / İlaç)"
        ctx["empty_text"] = "Geciken uygulama yok."
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
        messages.success(self.request, "Protokol oluşturuldu.")
        return super().form_valid(form)


class VaccineProtocolUpdateView(LoginRequiredMixin, UpdateView):
    model = VaccineDefinition
    form_class = VaccineDefinitionForm
    template_name = "vaccines/protocol_form.html"
    success_url = reverse_lazy("vaccines:protocols")

    def form_valid(self, form):
        messages.success(self.request, "Protokol güncellendi.")
        return super().form_valid(form)


@login_required
def definition_options(request):
    """Seçilen hayvanın türüne uygun aşı protokollerini döner (HTMX)."""
    patient_id = request.GET.get("patient")
    selected = request.GET.get("vaccine_definition") or request.GET.get("selected") or ""
    definitions = VaccineDefinition.objects.filter(active=True).select_related("species")
    if patient_id:
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient:
            definitions = definitions.filter(species_id=patient.species_id)
    return render(
        request,
        "vaccines/_definition_select.html",
        {"definitions": definitions, "selected": str(selected)},
    )


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
