"""Hatırlatma üretimi ve mesaj oluşturma servisleri."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.core.models import ClinicSettings

from .models import MessageTemplate, OutboundMessage, ReminderRule, render_body
from .providers import get_provider


def _clinic_sender() -> str:
    clinic = ClinicSettings.load()
    numbers = clinic.sender_numbers or []
    return numbers[0] if numbers else ""


def _appointment_context(appt, clinic_name: str) -> dict:
    return {
        "owner_name": appt.owner.full_name,
        "pet_name": appt.patient.name,
        "date": appt.starts_at.strftime("%d.%m.%Y"),
        "time": appt.starts_at.strftime("%H:%M"),
        "vaccine": "",
        "clinic": clinic_name,
    }


def _vaccine_context(record, clinic_name: str) -> dict:
    return {
        "owner_name": record.patient.owner.full_name,
        "pet_name": record.patient.name,
        "date": record.next_due_at.strftime("%d.%m.%Y") if record.next_due_at else "",
        "time": "",
        "vaccine": record.display_name,
        "clinic": clinic_name,
    }


def _create_message(*, owner, patient, kind, body, scheduled_for, dedupe_key, sender, provider,
                    appointment=None, vaccine_record=None) -> bool:
    """Tek mesaj üretir; iletişim tercihi/telefon uygunsa. True=oluşturuldu."""
    if owner.contact_pref == owner.ContactPref.NONE:
        return False
    if not owner.phone:
        return False
    if dedupe_key and OutboundMessage.objects.filter(dedupe_key=dedupe_key).exists():
        return False
    wa_link = provider.build_link(owner.phone, body)
    OutboundMessage.objects.create(
        owner=owner,
        patient=patient,
        kind=kind,
        sender_number=sender,
        to_phone=owner.phone,
        body=body,
        scheduled_for=scheduled_for,
        wa_link=wa_link,
        dedupe_key=dedupe_key,
        appointment=appointment,
        vaccine_record=vaccine_record,
    )
    return True


def generate_reminders(today=None) -> dict:
    """
    Aktif kurallara göre yaklaşan/geciken randevu ve aşılar için bekleyen mesaj üretir.
    Tekrar çalıştırılabilir (dedupe ile mükerrer üretmez). Sayıları döner.
    """
    from apps.appointments.models import Appointment
    from apps.vaccines.models import VaccineRecord

    today = today or timezone.localdate()
    clinic = ClinicSettings.load()
    sender = (clinic.sender_numbers or [""])[0]
    provider = get_provider()
    created = {"appointment": 0, "vaccine": 0}

    # --- Randevu kuralları ---
    appt_rules = ReminderRule.objects.filter(
        active=True, type=MessageTemplate.Type.APPOINTMENT, template__active=True
    ).select_related("template")
    for rule in appt_rules:
        target_date = today + timedelta(days=rule.offset_days)
        appts = Appointment.objects.filter(
            starts_at__date=target_date,
            status__in=[
                Appointment.Status.CONFIRMED,
                Appointment.Status.REQUESTED,
                Appointment.Status.ARRIVED,
            ],
        ).select_related("owner", "patient")
        for appt in appts:
            body = render_body(rule.template.body, _appointment_context(appt, clinic.name))
            key = f"appt:{appt.pk}:{rule.pk}:{target_date.isoformat()}"
            if _create_message(
                owner=appt.owner, patient=appt.patient,
                kind=OutboundMessage.KIND_APPOINTMENT, body=body,
                scheduled_for=today, dedupe_key=key, sender=sender,
                provider=provider, appointment=appt,
            ):
                created["appointment"] += 1

    # --- Aşı kuralları ---
    vac_rules = ReminderRule.objects.filter(
        active=True, type=MessageTemplate.Type.VACCINE, template__active=True
    ).select_related("template")
    for rule in vac_rules:
        target_date = today + timedelta(days=rule.offset_days)
        records = VaccineRecord.objects.filter(next_due_at=target_date).select_related(
            "patient", "patient__owner", "vaccine_definition"
        )
        for record in records:
            body = render_body(rule.template.body, _vaccine_context(record, clinic.name))
            key = f"vac:{record.pk}:{rule.pk}:{target_date.isoformat()}"
            if _create_message(
                owner=record.patient.owner, patient=record.patient,
                kind=OutboundMessage.KIND_VACCINE, body=body,
                scheduled_for=today, dedupe_key=key, sender=sender,
                provider=provider, vaccine_record=record,
            ):
                created["vaccine"] += 1

    created["total"] = created["appointment"] + created["vaccine"]
    return created
