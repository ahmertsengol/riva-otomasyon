from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView

from apps.core.models import ClinicSettings

from .forms import ManualMessageForm, MessageTemplateForm, ReminderRuleForm
from .models import MessageTemplate, OutboundMessage, ReminderRule
from .providers import get_provider
from .services import generate_reminders, get_template, render_template


@login_required
def render_template_view(request):
    """Seçilen şablonu, sahip/hayvan bağlamıyla doldurup düz metin döner (form JS için)."""
    from apps.owners.models import Owner
    from apps.patients.models import Patient

    tpl = MessageTemplate.objects.filter(pk=request.GET.get("template")).first()
    owner = Owner.objects.filter(pk=request.GET.get("owner")).first()
    patient = Patient.objects.filter(pk=request.GET.get("patient")).first()
    text = render_template(tpl, owner, patient) if tpl else ""
    return HttpResponse(text, content_type="text/plain; charset=utf-8")


@login_required
def queue(request):
    status = request.GET.get("status", OutboundMessage.PENDING)
    qs = OutboundMessage.objects.select_related("owner", "patient")
    if status in dict(OutboundMessage.STATUS_CHOICES):
        qs = qs.filter(status=status)
    status_tabs = [
        (value, label, OutboundMessage.objects.filter(status=value).count())
        for value, label in OutboundMessage.STATUS_CHOICES
    ]
    return render(
        request,
        "reminders/queue.html",
        {"messages_list": qs[:200], "active_status": status, "status_tabs": status_tabs},
    )


@login_required
@require_POST
def run_generate(request):
    result = generate_reminders()
    messages.success(
        request,
        f"{result['total']} hatırlatma üretildi "
        f"(randevu: {result['appointment']}, aşı: {result['vaccine']}).",
    )
    return redirect("reminders:queue")


@login_required
@require_POST
def mark_sent(request, pk):
    msg = get_object_or_404(OutboundMessage, pk=pk)
    msg.status = OutboundMessage.SENT
    msg.sent_at = timezone.now()
    msg.save(update_fields=["status", "sent_at", "updated_at", "updated_by"])
    messages.success(request, "Mesaj gönderildi olarak işaretlendi.")
    return redirect(request.META.get("HTTP_REFERER") or "reminders:queue")


@login_required
@require_POST
def create_appointment(request, pk):
    """Hatırlatmadan ilgili hayvan+sahip için randevu oluştur (aşı/parazit/ilaç → protokol+doz taşır)."""
    from datetime import datetime, timedelta
    from datetime import time as dtime

    from apps.appointments.models import Appointment

    msg = get_object_or_404(
        OutboundMessage.objects.select_related(
            "owner", "patient", "vaccine_record", "vaccine_record__vaccine_definition"
        ),
        pk=pk,
    )
    # Randevu hatırlatmasıysa zaten bir randevuya bağlıdır → mükerrer yaratma, ona git
    if msg.appointment_id:
        return redirect("appointments:detail", pk=msg.appointment_id)
    if not msg.patient_id:
        messages.error(request, "Bu mesajda hayvan bilgisi yok, randevu oluşturulamadı.")
        return redirect(request.META.get("HTTP_REFERER") or "reminders:queue")

    vr = msg.vaccine_record
    definition = vr.vaccine_definition if vr else None
    if vr and vr.next_due_at:
        starts_at = timezone.make_aware(datetime.combine(vr.next_due_at, dtime(10, 0)))
        appt_type = Appointment.CATEGORY_TO_TYPE.get(
            definition.category if definition else "", Appointment.Type.VACCINE
        )
        dose = vr.next_dose_number
    else:
        starts_at = timezone.now() + timedelta(days=1)
        appt_type, dose = Appointment.Type.GENERAL, None

    # Aynı protokol/gün için randevu varsa ona git (mükerrer önle)
    if definition:
        existing = Appointment.objects.filter(
            patient=msg.patient, protocol_definition=definition,
            starts_at__date=starts_at.date(),
        ).first()
        if existing:
            messages.info(request, "Bu doz için randevu zaten var.")
            return redirect("appointments:detail", pk=existing.pk)

    appt = Appointment.objects.create(
        owner=msg.owner, patient=msg.patient, starts_at=starts_at,
        type=appt_type, status=Appointment.Status.REQUESTED,
        source=Appointment.Source.AUTO_FOLLOWUP,
        protocol_definition=definition, dose_number=dose,
        note="Hatırlatmadan oluşturuldu.",
    )
    messages.success(request, "Randevu oluşturuldu.")
    return redirect("appointments:detail", pk=appt.pk)


@login_required
@require_POST
def cancel(request, pk):
    msg = get_object_or_404(OutboundMessage, pk=pk)
    msg.status = OutboundMessage.CANCELLED
    msg.save(update_fields=["status", "updated_at", "updated_by"])
    messages.info(request, "Mesaj iptal edildi.")
    return redirect(request.META.get("HTTP_REFERER") or "reminders:queue")


@login_required
@require_POST
def bulk_mark_sent(request):
    ids = request.POST.getlist("ids")
    updated = OutboundMessage.objects.filter(pk__in=ids, status=OutboundMessage.PENDING).update(
        status=OutboundMessage.SENT, sent_at=timezone.now()
    )
    messages.success(request, f"{updated} mesaj gönderildi olarak işaretlendi.")
    return redirect("reminders:queue")


class ManualMessageCreateView(LoginRequiredMixin, CreateView):
    model = OutboundMessage
    form_class = ManualMessageForm
    template_name = "reminders/manual_form.html"
    success_url = reverse_lazy("reminders:queue")

    def get_initial(self):
        from apps.owners.models import Owner
        from apps.patients.models import Patient

        initial = super().get_initial()
        owner = patient = None
        if owner_id := self.request.GET.get("owner"):
            initial["owner"] = owner_id
            owner = Owner.objects.filter(pk=owner_id).first()
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
            patient = Patient.objects.filter(pk=patient_id).first()
            if patient and not owner:
                owner = patient.owner
                initial["owner"] = owner.pk
        # Bağlamdan gelen olay (randevu/aşı vb.) → hazır şablonu seç ve gövdeyi doldur
        if key := self.request.GET.get("template_key"):
            tpl = get_template(key)
            if tpl:
                initial["template"] = tpl.pk
                initial["body"] = render_template(
                    tpl, owner, patient,
                    date=self.request.GET.get("date", ""),
                    time=self.request.GET.get("time", ""),
                    vaccine=self.request.GET.get("vaccine", ""),
                    amount=self.request.GET.get("amount", ""),
                )
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.patients.models import Patient

        owner_id = self.request.GET.get("owner")
        ctx["init_patients"] = (
            Patient.objects.filter(owner_id=owner_id).select_related("species").order_by("name")
            if owner_id
            else Patient.objects.none()
        )
        ctx["init_selected"] = self.request.GET.get("patient", "")
        ctx["init_has_owner"] = bool(owner_id)
        return ctx

    def form_valid(self, form):
        clinic = ClinicSettings.load()
        provider = get_provider()
        msg = form.instance
        msg.kind = OutboundMessage.KIND_MANUAL
        msg.to_phone = form.cleaned_data["owner"].phone
        msg.sender_number = (clinic.sender_numbers or [""])[0]
        msg.wa_link = provider.build_link(msg.to_phone, msg.body)
        messages.success(self.request, "Mesaj kuyruğa eklendi.")
        return super().form_valid(form)


# --- Şablonlar & Kurallar ---
@login_required
def templates_and_rules(request):
    return render(
        request,
        "reminders/templates.html",
        {
            "templates": MessageTemplate.objects.all(),
            "rules": ReminderRule.objects.select_related("template").all(),
        },
    )


class MessageTemplateCreateView(LoginRequiredMixin, CreateView):
    model = MessageTemplate
    form_class = MessageTemplateForm
    template_name = "reminders/template_form.html"
    success_url = reverse_lazy("reminders:templates")

    def form_valid(self, form):
        messages.success(self.request, "Şablon kaydedildi.")
        return super().form_valid(form)


class MessageTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = MessageTemplate
    form_class = MessageTemplateForm
    template_name = "reminders/template_form.html"
    success_url = reverse_lazy("reminders:templates")

    def form_valid(self, form):
        messages.success(self.request, "Şablon güncellendi.")
        return super().form_valid(form)


class ReminderRuleCreateView(LoginRequiredMixin, CreateView):
    model = ReminderRule
    form_class = ReminderRuleForm
    template_name = "reminders/rule_form.html"
    success_url = reverse_lazy("reminders:templates")

    def form_valid(self, form):
        messages.success(self.request, "Kural kaydedildi.")
        return super().form_valid(form)


class ReminderRuleUpdateView(LoginRequiredMixin, UpdateView):
    model = ReminderRule
    form_class = ReminderRuleForm
    template_name = "reminders/rule_form.html"
    success_url = reverse_lazy("reminders:templates")

    def form_valid(self, form):
        messages.success(self.request, "Kural güncellendi.")
        return super().form_valid(form)
