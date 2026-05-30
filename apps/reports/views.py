"""MVP raporları — sorgu tabanlı (yeni model yok)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date


@login_required
def index(request):
    from apps.appointments.models import Appointment
    from apps.billing.models import Charge, Payment
    from apps.medical.models import Examination
    from apps.owners.models import Owner
    from apps.patients.models import Patient
    from apps.reminders.models import OutboundMessage
    from apps.vaccines.models import VaccineRecord

    today = timezone.localdate()
    day = parse_date(request.GET.get("date", "")) or today
    soon = day + timedelta(days=30)

    daily = {
        "appointments": Appointment.objects.filter(starts_at__date=day)
        .exclude(status=Appointment.Status.CANCELLED).count(),
        "exams": Examination.objects.filter(created_at__date=day).count(),
        "new_owners": Owner.objects.filter(created_at__date=day).count(),
        "new_patients": Patient.objects.filter(created_at__date=day).count(),
        "messages_sent": OutboundMessage.objects.filter(
            status=OutboundMessage.SENT, sent_at__date=day
        ).count(),
        "collection": Payment.objects.filter(paid_at__date=day).aggregate(t=Sum("amount"))["t"]
        or Decimal("0"),
    }

    vaccines = {
        "upcoming": VaccineRecord.objects.filter(next_due_at__gte=day, next_due_at__lte=soon).count(),
        "overdue": VaccineRecord.objects.filter(next_due_at__lt=today).count(),
    }

    unpaid_qs = Charge.objects.exclude(status=Charge.PAID)
    unpaid = {
        "count": unpaid_qs.count(),
        # Kalan bakiye toplamı = Σtotal − Σ(ödenen)
        "outstanding": (unpaid_qs.aggregate(t=Sum("total"))["t"] or Decimal("0"))
        - (
            Payment.objects.filter(charge__in=unpaid_qs).aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        ),
    }

    return render(
        request,
        "reports/index.html",
        {
            "day": day,
            "is_today": day == today,
            "daily": daily,
            "vaccines": vaccines,
            "unpaid": unpaid,
        },
    )
