from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView

from apps.core.models import ClinicSettings

from .forms import ManualMessageForm, MessageTemplateForm, ReminderRuleForm
from .models import MessageTemplate, OutboundMessage, ReminderRule
from .providers import get_provider
from .services import generate_reminders


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
        initial = super().get_initial()
        if owner_id := self.request.GET.get("owner"):
            initial["owner"] = owner_id
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
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
