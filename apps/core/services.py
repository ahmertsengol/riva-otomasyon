"""
Panel verisi ve global arama servisleri.

Diğer modüller (owners, patients, appointments, vaccines, billing, reminders)
geliştikçe burada doldurulur. İlgili modül henüz yoksa servis sessizce 0/boş döner;
böylece panel her aşamada çalışır.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone


def _safe(fn, default=0):
    try:
        return fn()
    except Exception:
        return default


def dashboard_context() -> dict:
    today = timezone.localdate()
    soon = today + timedelta(days=7)
    ctx = {
        "today": today,
        "cards": {},
        "today_appointments": [],
    }

    def appointments_today():
        from apps.appointments.models import Appointment

        return Appointment.objects.filter(
            starts_at__date=today
        ).exclude(status=Appointment.Status.CANCELLED)

    def pending_requests():
        from apps.appointments.models import AppointmentRequest

        return AppointmentRequest.objects.filter(status=AppointmentRequest.NEW).count()

    def upcoming_vaccines():
        from apps.vaccines.models import VaccineRecord

        return VaccineRecord.objects.filter(
            next_due_at__gte=today, next_due_at__lte=soon
        ).count()

    def overdue_vaccines():
        from apps.vaccines.models import VaccineRecord

        return VaccineRecord.objects.filter(next_due_at__lt=today).count()

    def exams_today():
        from apps.medical.models import Examination

        return Examination.objects.filter(created_at__date=today).count()

    def new_owners():
        from apps.owners.models import Owner

        return Owner.objects.filter(created_at__date=today).count()

    def new_patients():
        from apps.patients.models import Patient

        return Patient.objects.filter(created_at__date=today).count()

    def pending_messages():
        from apps.reminders.models import OutboundMessage

        return OutboundMessage.objects.filter(status=OutboundMessage.PENDING).count()

    def failed_messages():
        from apps.reminders.models import OutboundMessage

        return OutboundMessage.objects.filter(status=OutboundMessage.FAILED).count()

    def todays_collection():
        from django.db.models import Sum

        from apps.billing.models import Payment

        agg = Payment.objects.filter(paid_at__date=today).aggregate(t=Sum("amount"))
        return agg["t"] or 0

    ctx["cards"] = {
        "appointments_today": _safe(lambda: appointments_today().count()),
        "pending_requests": _safe(pending_requests),
        "upcoming_vaccines": _safe(upcoming_vaccines),
        "overdue_vaccines": _safe(overdue_vaccines),
        "exams_today": _safe(exams_today),
        "new_owners": _safe(new_owners),
        "new_patients": _safe(new_patients),
        "pending_messages": _safe(pending_messages),
        "failed_messages": _safe(failed_messages),
        "todays_collection": _safe(todays_collection, 0),
    }
    tomorrow = today + timedelta(days=1)
    ctx["tomorrow"] = tomorrow

    def appts_on(day):
        from apps.appointments.models import Appointment

        return list(
            Appointment.objects.filter(starts_at__date=day)
            .exclude(status=Appointment.Status.CANCELLED)
            .select_related("patient", "owner", "assigned_vet", "protocol_definition")
            .order_by("starts_at")
        )

    def due_protocols_on(day):
        from apps.appointments.models import Appointment
        from apps.vaccines.models import VaccineRecord

        # O gün için zaten protokol randevusu olan (hayvan, protokol) çiftleri → due'da tekrar gösterme
        booked = set(
            Appointment.objects.filter(
                starts_at__date=day, protocol_definition__isnull=False
            )
            .exclude(status=Appointment.Status.CANCELLED)
            .values_list("patient_id", "protocol_definition_id")
        )
        records = (
            VaccineRecord.objects.filter(next_due_at=day)
            .select_related("patient", "patient__owner", "vaccine_definition")
            .order_by("patient__name")
        )
        return [
            r for r in records
            if (r.patient_id, r.vaccine_definition_id) not in booked
        ]

    def pending_reminder_list():
        from apps.reminders.models import OutboundMessage

        return list(
            OutboundMessage.objects.filter(status=OutboundMessage.PENDING)
            .select_related("owner", "patient")[:50]
        )

    ctx["today_appointments"] = _safe(lambda: appts_on(today), [])
    ctx["tomorrow_appointments"] = _safe(lambda: appts_on(tomorrow), [])
    ctx["due_today"] = _safe(lambda: due_protocols_on(today), [])
    ctx["due_tomorrow"] = _safe(lambda: due_protocols_on(tomorrow), [])
    ctx["pending_reminders"] = _safe(pending_reminder_list, [])
    return ctx


def global_search(query: str) -> dict:
    """Telefon, sahip adı, hayvan adı ve mikroçip numarasıyla hızlı arama."""
    results = {"owners": [], "patients": []}

    def owners():
        from apps.owners.models import Owner

        return list(
            Owner.objects.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(phone__icontains=query)
            )[:20]
        )

    def patients():
        from apps.patients.models import Patient

        return list(
            Patient.objects.select_related("owner", "species").filter(
                Q(name__icontains=query) | Q(microchip_no__icontains=query)
            )[:20]
        )

    results["owners"] = _safe(owners, [])
    results["patients"] = _safe(patients, [])
    return results
