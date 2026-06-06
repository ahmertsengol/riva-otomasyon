from __future__ import annotations

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from apps.accounts.models import User

from .forms import AppointmentForm, QuickIntakeForm
from .models import Appointment, AppointmentRequest


@transaction.atomic
def _do_quick_intake(form, user):
    """Tek transaction: sahip/hayvan (gerekirse) + walk-in randevu (muayenede) + muayene."""
    from apps.medical.models import Examination
    from apps.owners.models import Owner
    from apps.patients.models import Patient

    cd = form.cleaned_data
    existing_patient = cd.get("patient")
    # Sahip: seçilen > (mevcut hayvanın sahibi) > yeni oluştur. Böylece sahipsiz
    # mevcut hayvan seçilse bile boş/yanlış sahip oluşmaz (savunmacı).
    owner = cd.get("owner") or (existing_patient.owner if existing_patient else None)
    if owner is None:
        owner = Owner.objects.create(
            first_name=cd["new_owner_first"], last_name=cd.get("new_owner_last", ""),
            phone=cd["new_owner_phone"], contact_pref=Owner.ContactPref.WHATSAPP,
        )
    patient = existing_patient or Patient.objects.create(
        owner=owner, name=cd["new_pet_name"], species=cd["new_pet_species"],
        breed=cd.get("new_pet_breed", ""), sex=cd.get("new_pet_sex") or Patient.Sex.UNKNOWN,
    )
    vet = cd.get("vet")
    if not vet and getattr(user, "role", None) in {User.Role.VET, User.Role.ADMIN}:
        vet = user
    appt = Appointment.objects.create(
        owner=owner, patient=patient, phone_snapshot=owner.phone,
        starts_at=timezone.now(), duration_min=20, type=cd["type"],
        status=Appointment.Status.IN_EXAM, source=Appointment.Source.WALK_IN,
        reminder_enabled=False, assigned_vet=vet, note=cd.get("complaint", ""),
    )
    return Examination.objects.create(
        patient=patient, appointment=appt, vet=vet, complaint=cd.get("complaint", ""),
    )


def _patient_filter_ctx(owner_id, selected):
    """Randevu formunda sahip→hayvan filtresi için başlangıç hayvan listesi."""
    from apps.patients.models import Patient

    patients = (
        Patient.objects.filter(owner_id=owner_id).select_related("species").order_by("name")
        if owner_id
        else Patient.objects.none()
    )
    return {
        "init_patients": patients,
        "init_selected": str(selected or ""),
        "init_has_owner": bool(owner_id),
    }


@login_required
def quick_intake(request):
    """Randevusuz (walk-in) hasta kabul ekranı."""
    if request.method == "POST":
        form = QuickIntakeForm(request.POST)
        if form.is_valid():
            exam = _do_quick_intake(form, request.user)
            messages.success(request, "Hasta kabul edildi, muayene açıldı.")
            return redirect("medical:examination_detail", pk=exam.pk)
    else:
        form = QuickIntakeForm()
    return render(request, "appointments/quick_intake.html", {"form": form})


@login_required
def calendar(request):
    vets = User.objects.filter(role__in=[User.Role.VET, User.Role.ADMIN], is_active=True)
    return render(
        request,
        "appointments/calendar.html",
        {
            "vets": vets,
            "statuses": Appointment.Status.choices,
            "types": Appointment.Type.choices,
        },
    )


@login_required
def events(request):
    """FullCalendar için JSON olay akışı (hekim/durum/tip filtreli)."""
    qs = Appointment.objects.select_related(
        "patient", "owner", "assigned_vet", "protocol_definition"
    )
    if start := request.GET.get("start"):
        qs = qs.filter(starts_at__gte=parse_datetime(start))
    if end := request.GET.get("end"):
        qs = qs.filter(starts_at__lte=parse_datetime(end))
    if vet := request.GET.get("vet"):
        qs = qs.filter(assigned_vet_id=vet)
    if status := request.GET.get("status"):
        qs = qs.filter(status=status)
    if atype := request.GET.get("type"):
        qs = qs.filter(type=atype)

    data = [
        {
            "id": a.pk,
            "title": a.patient.name,
            "start": a.starts_at.isoformat(),
            "end": (a.starts_at + timedelta(minutes=a.duration_min)).isoformat(),
            "color": a.color,
            "url": reverse("appointments:detail", args=[a.pk]),
            "extendedProps": {
                "status": a.get_status_display(),
                "status_code": a.status,
                "type": a.protocol_label,
                "owner": a.owner.full_name,
                "phone": a.phone_snapshot or a.owner.phone,
                "vet": a.assigned_vet.display_name if a.assigned_vet else "",
            },
        }
        for a in qs
    ]
    return JsonResponse(data, safe=False)


@login_required
@require_POST
def reschedule(request):
    """Sürükle-bırak/yeniden boyutlandırma ile randevu tarih/süre güncelleme."""
    appt = get_object_or_404(Appointment, pk=request.POST.get("id"))
    start = parse_datetime(request.POST.get("start") or "")
    if not start:
        return JsonResponse({"ok": False, "error": "geçersiz tarih"}, status=400)
    appt.starts_at = start
    if end := parse_datetime(request.POST.get("end") or ""):
        minutes = int((end - start).total_seconds() // 60)
        if minutes > 0:
            appt.duration_min = minutes
    appt.save()
    return JsonResponse({"ok": True})


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "appointments/form.html"

    def get_initial(self):
        initial = super().get_initial()
        if pid := self.request.GET.get("patient"):
            initial["patient"] = pid
            from apps.patients.models import Patient

            patient = Patient.objects.filter(pk=pid).first()
            if patient:
                initial["owner"] = patient.owner_id
        if oid := self.request.GET.get("owner"):
            initial["owner"] = oid
        if d := self.request.GET.get("date"):
            initial["starts_at"] = d
        if rid := self.request.GET.get("from_request"):
            req = AppointmentRequest.objects.filter(pk=rid).first()
            if req:
                initial["note"] = (
                    f"[Talep] {req.name} · {req.phone}\n"
                    f"{req.pet_name} ({req.pet_species}) · {req.subject}\n{req.message}"
                ).strip()
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_patient_filter_ctx(ctx["form"]["owner"].value(), ctx["form"]["patient"].value()))
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        rid = self.request.GET.get("from_request")
        if rid:
            Appointment.objects.filter(pk=self.object.pk).update(
                source=Appointment.Source.ONLINE_REQUEST
            )
            AppointmentRequest.objects.filter(pk=rid).update(
                status=AppointmentRequest.CONVERTED, linked_appointment=self.object
            )
        messages.success(self.request, "Randevu oluşturuldu.")
        return response


class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = "appointments/detail.html"
    context_object_name = "appt"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = Appointment.Status.choices
        return ctx


class AppointmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "appointments/form.html"

    def get_initial(self):
        initial = super().get_initial()
        if self.object and self.object.owner_id:
            initial["owner"] = self.object.owner_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_patient_filter_ctx(ctx["form"]["owner"].value(), ctx["form"]["patient"].value()))
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Randevu güncellendi.")
        return super().form_valid(form)


class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Appointment
    template_name = "appointments/confirm_delete.html"
    context_object_name = "appt"
    success_url = reverse_lazy("appointments:calendar")

    def form_valid(self, form):
        messages.success(self.request, "Randevu silindi.")
        return super().form_valid(form)


@login_required
@require_POST
def set_status(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    status = request.POST.get("status")
    if status in dict(Appointment.Status.choices):
        appt.status = status
        appt.save(update_fields=["status", "updated_at", "updated_by"])
        messages.success(request, "Durum güncellendi.")
    return redirect("appointments:detail", pk=pk)


@login_required
@require_POST
def start_exam(request, pk):
    """Randevuyu 'Muayenede'ye al + (yoksa) muayeneyi aç → muayene ekranına git."""
    from apps.medical.models import Examination

    appt = get_object_or_404(Appointment.objects.select_related("patient", "assigned_vet"), pk=pk)
    exam = Examination.objects.filter(appointment=appt).first()
    if not exam:
        exam = Examination.objects.create(
            patient=appt.patient, appointment=appt,
            vet=appt.assigned_vet, complaint=appt.note or "",
        )
    if appt.status != Appointment.Status.COMPLETED:
        appt.status = Appointment.Status.IN_EXAM
        appt.save()
    messages.success(request, "Hasta muayeneye alındı.")
    return redirect("medical:examination_detail", pk=exam.pk)


# ---------------------------------------------------------------------------
# Randevu Talepleri
# ---------------------------------------------------------------------------
@login_required
def request_list(request):
    requests_qs = AppointmentRequest.objects.all()
    status = request.GET.get("status", AppointmentRequest.NEW)
    if status in dict(AppointmentRequest.STATUS_CHOICES):
        requests_qs = requests_qs.filter(status=status)
    return render(
        request,
        "appointments/requests.html",
        {"requests": requests_qs, "active_status": status},
    )


@login_required
@require_POST
def request_dismiss(request, pk):
    AppointmentRequest.objects.filter(pk=pk).update(status=AppointmentRequest.DISMISSED)
    messages.info(request, "Talep yok sayıldı.")
    return redirect("appointments:request_list")


@csrf_exempt
@require_POST
def api_create_request(request):
    """
    Landing page'den gelen randevu talebi (public). MVP'de landing henüz bağlı değil;
    endpoint hazır bırakılır (bkz. docs/LANDING_INTEGRATION.md).
    """
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not name or not phone:
        return JsonResponse({"ok": False, "error": "name and phone required"}, status=400)

    AppointmentRequest.objects.create(
        name=name[:160],
        phone=phone[:30],
        pet_name=(payload.get("pet_name") or "")[:80],
        pet_species=(payload.get("pet_species") or "")[:60],
        requested_at=(payload.get("requested_at") or "")[:120],
        subject=(payload.get("subject") or "")[:120],
        message=payload.get("message") or "",
        source=AppointmentRequest.SOURCE_WEB,
    )
    return JsonResponse({"ok": True})
