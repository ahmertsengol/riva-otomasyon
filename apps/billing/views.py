from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.models import ClinicSettings
from apps.owners.models import Owner

from .forms import ChargeForm, ChargeLineFormSet, PaymentForm, ServiceItemForm
from .models import Charge, Payment, ServiceItem


@login_required
def index(request):
    today = timezone.localdate()
    payments_today = Payment.objects.filter(paid_at__date=today)
    summary = {
        "collection_today": payments_today.aggregate(t=Sum("amount"))["t"] or Decimal("0"),
        "payment_count": payments_today.count(),
        "pending_charges": Charge.objects.exclude(status=Charge.PAID).count(),
    }
    method_labels = dict(Payment.Method.choices)
    by_method = [
        {"label": method_labels.get(row["method"], row["method"]), "total": row["total"]}
        for row in payments_today.values("method").annotate(total=Sum("amount")).order_by("-total")
    ]
    recent_charges = Charge.objects.select_related("owner", "patient").all()[:15]
    # Borçlu sahipler: Σ charge.total − Σ payment > 0
    # (Subquery ile; tek sorguda iki Sum JOIN çarpımı yaratırdı.)
    charged_sq = (
        Charge.objects.filter(owner=OuterRef("pk")).values("owner")
        .annotate(s=Sum("total")).values("s")
    )
    paid_sq = (
        Payment.objects.filter(charge__owner=OuterRef("pk")).values("charge__owner")
        .annotate(s=Sum("amount")).values("s")
    )
    dec = DecimalField(max_digits=12, decimal_places=2)
    debtors = (
        Owner.objects.annotate(
            charged=Coalesce(Subquery(charged_sq, output_field=dec), Value(0), output_field=dec),
            paid=Coalesce(Subquery(paid_sq, output_field=dec), Value(0), output_field=dec),
        )
        .annotate(debt=F("charged") - F("paid"))
        .filter(debt__gt=0)
        .order_by("-debt")[:15]
    )
    return render(
        request,
        "billing/index.html",
        {
            "summary": summary,
            "by_method": by_method,
            "recent_charges": recent_charges,
            "debtors": debtors,
        },
    )


class ChargeCreateView(LoginRequiredMixin, CreateView):
    model = Charge
    form_class = ChargeForm
    template_name = "billing/charge_form.html"

    def get_initial(self):
        initial = super().get_initial()
        for key in ("owner", "patient", "examination"):
            if val := self.request.GET.get(key):
                initial[key] = val
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = ChargeLineFormSet(self.request.POST)
        else:
            ctx["formset"] = ChargeLineFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if not formset.is_valid():
            return self.form_invalid(form)
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        self.object.recompute()
        messages.success(self.request, "İşlem oluşturuldu.")
        return redirect(self.object.get_absolute_url())


@login_required
def charge_detail(request, pk):
    charge = get_object_or_404(
        Charge.objects.select_related("owner", "patient", "examination"), pk=pk
    )
    return render(
        request,
        "billing/charge_detail.html",
        {"charge": charge, "lines": charge.lines.all(), "payments": charge.payments.all()},
    )


@login_required
def payment_create(request, charge_pk=None):
    charge = get_object_or_404(Charge, pk=charge_pk) if charge_pk else None
    if request.method == "POST":
        form = PaymentForm(request.POST, fix_charge=charge)
        if form.is_valid():
            payment = form.save()
            payment.charge.recompute()
            messages.success(request, "Tahsilat kaydedildi.")
            return redirect(payment.charge.get_absolute_url())
    else:
        initial = {}
        if charge:
            initial["amount"] = charge.balance
        form = PaymentForm(fix_charge=charge, initial=initial)
    return render(request, "billing/payment_form.html", {"form": form, "charge": charge})


@login_required
def e_invoice_sim(request, pk):
    charge = get_object_or_404(
        Charge.objects.select_related("owner", "patient"), pk=pk
    )
    return render(
        request,
        "billing/e_invoice_sim.html",
        {"charge": charge, "lines": charge.lines.all(), "clinic": ClinicSettings.load()},
    )


class ServiceItemListView(LoginRequiredMixin, ListView):
    model = ServiceItem
    template_name = "billing/services.html"
    context_object_name = "items"


class ServiceItemCreateView(LoginRequiredMixin, CreateView):
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = "billing/service_form.html"
    success_url = reverse_lazy("billing:services")

    def form_valid(self, form):
        messages.success(self.request, "Hizmet/ürün eklendi.")
        return super().form_valid(form)


class ServiceItemUpdateView(LoginRequiredMixin, UpdateView):
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = "billing/service_form.html"
    success_url = reverse_lazy("billing:services")

    def form_valid(self, form):
        messages.success(self.request, "Hizmet/ürün güncellendi.")
        return super().form_valid(form)
