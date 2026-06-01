from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.generic import CreateView, DetailView, ListView, View

from apps.accounts.models import User
from apps.core.models import ClinicSettings

from .forms import (
    ExaminationForm,
    LabResultForm,
    NoteForm,
    OperationForm,
    PrescriptionForm,
    PrescriptionItemFormSet,
)
from .models import Examination, LabResult, Note, Operation, Prescription


class ExaminationListView(LoginRequiredMixin, ListView):
    model = Examination
    template_name = "medical/examination_list.html"
    context_object_name = "examinations"
    paginate_by = 30

    def get_queryset(self):
        return (
            Examination.objects.select_related("patient", "patient__owner", "vet")
            .all()
            .order_by("-created_at")
        )


class ExaminationCreateView(LoginRequiredMixin, CreateView):
    model = Examination
    form_class = ExaminationForm
    template_name = "medical/examination_form.html"

    def get_initial(self):
        initial = super().get_initial()
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
        if appointment_id := self.request.GET.get("appointment"):
            initial["appointment"] = appointment_id
            try:
                from apps.appointments.models import Appointment

                appt = Appointment.objects.select_related("patient", "assigned_vet").get(
                    pk=appointment_id
                )
                initial["patient"] = appt.patient_id
                if appt.assigned_vet_id:
                    initial["vet"] = appt.assigned_vet_id
            except Exception:
                pass
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
        messages.success(self.request, "Muayene kaydı oluşturuldu.")
        return super().form_valid(form)


class ExaminationDetailView(LoginRequiredMixin, DetailView):
    model = Examination
    template_name = "medical/examination_detail.html"
    context_object_name = "exam"

    def get_queryset(self):
        return Examination.objects.select_related("patient", "patient__owner", "vet", "appointment")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prescriptions"] = self.object.prescriptions.prefetch_related("items").all()
        ctx["lab_results"] = self.object.lab_results.all()
        return ctx


class PrescriptionCreateView(LoginRequiredMixin, View):
    template_name = "medical/prescription_form.html"

    def get_initial(self):
        initial = {}
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
        if exam_id := self.request.GET.get("examination"):
            initial["examination"] = exam_id
            try:
                exam = Examination.objects.select_related("patient", "vet").get(pk=exam_id)
                initial["patient"] = exam.patient_id
                if exam.vet_id:
                    initial["vet"] = exam.vet_id
            except Exception:
                pass
        user = self.request.user
        if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in {
            User.Role.VET,
            User.Role.ADMIN,
        }:
            initial.setdefault("vet", user.pk)
        return initial

    def _exam_ctx(self, patient_id, selected=""):
        exams = (
            Examination.objects.filter(patient_id=patient_id).select_related("vet").order_by("-created_at")
            if patient_id
            else Examination.objects.none()
        )
        return {"init_examinations": exams, "init_exam_selected": str(selected or "")}

    def get(self, request):
        prescription = Prescription()
        initial = self.get_initial()
        form = PrescriptionForm(initial=initial, instance=prescription)
        formset = PrescriptionItemFormSet(instance=prescription)
        ctx = {"form": form, "formset": formset, **self._exam_ctx(initial.get("patient"), initial.get("examination", ""))}
        return render(request, self.template_name, ctx)

    def post(self, request):
        prescription = Prescription()
        form = PrescriptionForm(request.POST, instance=prescription)
        formset = PrescriptionItemFormSet(request.POST, instance=prescription)
        if form.is_valid() and formset.is_valid():
            prescription = form.save(commit=False)
            if not prescription.vet_id and request.user.is_authenticated:
                prescription.vet = request.user
            prescription.save()
            formset.instance = prescription
            formset.save()
            messages.success(request, "Reçete oluşturuldu.")
            return redirect(prescription)
        ctx = {"form": form, "formset": formset, **self._exam_ctx(request.POST.get("patient"), request.POST.get("examination", ""))}
        return render(request, self.template_name, ctx)


class PrescriptionDetailView(LoginRequiredMixin, DetailView):
    model = Prescription
    template_name = "medical/prescription_detail.html"
    context_object_name = "prescription"

    def get_queryset(self):
        return Prescription.objects.select_related(
            "patient", "patient__owner", "patient__species", "vet", "examination"
        ).prefetch_related("items")


@login_required
def prescription_pdf(request, pk):
    prescription = get_object_or_404(
        Prescription.objects.select_related(
            "patient", "patient__owner", "patient__species", "vet", "examination"
        ).prefetch_related("items"),
        pk=pk,
    )
    html = render_to_string(
        "medical/prescription_pdf.html",
        {"prescription": prescription, "clinic": ClinicSettings.load()},
        request=request,
    )
    from weasyprint import HTML

    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="recete-{prescription.pk}.pdf"'
    return response


@login_required
def examination_options(request):
    """Seçilen hayvanın muayenelerini döner (HTMX ile reçete/lab formlarında filtre)."""
    patient_id = request.GET.get("patient")
    selected = request.GET.get("examination") or request.GET.get("selected") or ""
    exams = (
        Examination.objects.filter(patient_id=patient_id).select_related("vet").order_by("-created_at")
        if patient_id
        else Examination.objects.none()
    )
    return render(
        request,
        "medical/_examination_select.html",
        {"examinations": exams, "selected": str(selected)},
    )


class PatientInitialMixin:
    def get_initial(self):
        initial = super().get_initial()
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        patient_id = self.request.GET.get("patient")
        ctx["init_examinations"] = (
            Examination.objects.filter(patient_id=patient_id).select_related("vet").order_by("-created_at")
            if patient_id
            else Examination.objects.none()
        )
        ctx["init_exam_selected"] = self.request.GET.get("examination", "")
        return ctx

    def assign_current_vet(self, form):
        if hasattr(form.instance, "vet_id") and not form.instance.vet_id:
            user = self.request.user
            if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in {
                User.Role.VET,
                User.Role.ADMIN,
            }:
                form.instance.vet = user


class OperationCreateView(LoginRequiredMixin, PatientInitialMixin, CreateView):
    model = Operation
    form_class = OperationForm
    template_name = "medical/operation_form.html"

    def get_initial(self):
        initial = super().get_initial()
        from django.utils import timezone

        initial.setdefault("date", timezone.localtime().strftime("%Y-%m-%dT%H:%M"))
        user = self.request.user
        if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in {
            User.Role.VET,
            User.Role.ADMIN,
        }:
            initial.setdefault("vet", user.pk)
        return initial

    def form_valid(self, form):
        self.assign_current_vet(form)
        messages.success(self.request, "Operasyon kaydı oluşturuldu.")
        return super().form_valid(form)


class OperationDetailView(LoginRequiredMixin, DetailView):
    model = Operation
    template_name = "medical/operation_detail.html"
    context_object_name = "operation"

    def get_queryset(self):
        return Operation.objects.select_related("patient", "patient__owner", "patient__species", "vet")


class LabResultCreateView(LoginRequiredMixin, PatientInitialMixin, CreateView):
    model = LabResult
    form_class = LabResultForm
    template_name = "medical/lab_result_form.html"

    def get_initial(self):
        initial = super().get_initial()
        if exam_id := self.request.GET.get("examination"):
            initial["examination"] = exam_id
            try:
                exam = Examination.objects.select_related("patient").get(pk=exam_id)
                initial["patient"] = exam.patient_id
            except Exception:
                pass
        from django.utils import timezone

        initial.setdefault("date", timezone.localdate())
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Laboratuvar sonucu kaydedildi.")
        return super().form_valid(form)


class LabResultDetailView(LoginRequiredMixin, DetailView):
    model = LabResult
    template_name = "medical/lab_result_detail.html"
    context_object_name = "lab"

    def get_queryset(self):
        return LabResult.objects.select_related(
            "patient", "patient__owner", "patient__species", "examination"
        )


class NoteCreateView(LoginRequiredMixin, PatientInitialMixin, CreateView):
    model = Note
    form_class = NoteForm
    template_name = "medical/note_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Tıbbi not kaydedildi.")
        return super().form_valid(form)


class NoteDetailView(LoginRequiredMixin, DetailView):
    model = Note
    template_name = "medical/note_detail.html"
    context_object_name = "note"

    def get_queryset(self):
        return Note.objects.select_related("patient", "patient__owner", "patient__species")
