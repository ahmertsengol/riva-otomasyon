from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import OwnerForm
from .models import Owner


class OwnerListView(LoginRequiredMixin, ListView):
    model = Owner
    template_name = "owners/list.html"
    context_object_name = "owners"
    paginate_by = 25

    def get_queryset(self):
        qs = Owner.objects.annotate(pet_count=Count("patients")).order_by(
            "first_name", "last_name"
        )
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class OwnerDetailView(LoginRequiredMixin, DetailView):
    model = Owner
    template_name = "owners/detail.html"
    context_object_name = "owner"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["patients"] = self.object.patients.select_related("species").all()
        try:
            from apps.appointments.models import Appointment

            ctx["appointments"] = (
                Appointment.objects.filter(owner=self.object)
                .select_related("patient", "assigned_vet")
                .order_by("-starts_at")
            )
        except Exception:
            ctx["appointments"] = []
        try:
            from apps.billing.models import Charge

            ctx["charges"] = (
                Charge.objects.filter(owner=self.object).select_related("patient").order_by("-date")
            )
        except Exception:
            ctx["charges"] = []
        try:
            from apps.reminders.models import OutboundMessage

            ctx["messages_log"] = (
                OutboundMessage.objects.filter(owner=self.object).order_by("-created_at")[:30]
            )
        except Exception:
            ctx["messages_log"] = []
        return ctx


class OwnerCreateView(LoginRequiredMixin, CreateView):
    model = Owner
    form_class = OwnerForm
    template_name = "owners/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Sahip kaydı oluşturuldu.")
        return super().form_valid(form)


class OwnerUpdateView(LoginRequiredMixin, UpdateView):
    model = Owner
    form_class = OwnerForm
    template_name = "owners/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Sahip kaydı güncellendi.")
        return super().form_valid(form)


class OwnerDeleteView(LoginRequiredMixin, DeleteView):
    model = Owner
    template_name = "owners/confirm_delete.html"
    success_url = reverse_lazy("owners:list")

    def form_valid(self, form):
        messages.success(self.request, "Sahip kaydı silindi.")
        return super().form_valid(form)
