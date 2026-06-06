"""Hatırlatma üretimi, şablon doldurma ve mesaj oluşturma servisleri."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.core.models import ClinicSettings

from .models import MessageTemplate, OutboundMessage, ReminderRule, render_body
from .providers import get_provider

# Protokol kategorisi → şablon anahtarı öneki (ör. "ic-parazit-yaklasan")
CATEGORY_TEMPLATE_PREFIX = {
    "vaccine": "asi",
    "internal_parasite": "ic-parazit",
    "external_parasite": "dis-parazit",
    "medication": "ilac",
}


def build_context(owner=None, patient=None, *, clinic_name=None, date="", time="",
                  vaccine="", amount="") -> dict:
    """Şablon yer tutucu değerleri. clinic_name verilmezse bir kez yüklenir."""
    if clinic_name is None:
        clinic_name = ClinicSettings.load().name
    return {
        "owner_name": owner.full_name if owner else "",
        "pet_name": patient.name if patient else "",
        "species": patient.species.name if patient and patient.species_id else "",
        "phone": owner.phone if owner else "",
        "date": date,
        "time": time,
        "vaccine": vaccine,
        "amount": amount,
        "clinic": clinic_name,
    }


def get_template(key: str, locale: str = "tr") -> MessageTemplate | None:
    """Anahtara göre aktif şablon (yoksa pasifi de dener)."""
    return (
        MessageTemplate.objects.filter(key=key, active=True).first()
        or MessageTemplate.objects.filter(key=key).first()
    )


def render_template(template: MessageTemplate, owner=None, patient=None, **extra) -> str:
    if not template:
        return ""
    return render_body(template.body, build_context(owner, patient, **extra))


def _create_message(*, owner, patient, kind, body, scheduled_for, dedupe_key, sender, provider,
                    appointment=None, vaccine_record=None) -> bool:
    """Tek mesaj üretir; iletişim tercihi/telefon uygunsa. True=oluşturuldu."""
    if owner.contact_pref == owner.ContactPref.NONE:
        return False
    if not owner.phone:
        return False
    if dedupe_key and OutboundMessage.objects.filter(dedupe_key=dedupe_key).exists():
        return False
    OutboundMessage.objects.create(
        owner=owner,
        patient=patient,
        kind=kind,
        sender_number=sender,
        to_phone=owner.phone,
        body=body,
        scheduled_for=scheduled_for,
        wa_link=provider.build_link(owner.phone, body),
        dedupe_key=dedupe_key,
        appointment=appointment,
        vaccine_record=vaccine_record,
    )
    return True


def generate_reminders(today=None) -> dict:
    """
    Aktif kurallara göre yaklaşan/geciken randevu ve aşılar için bekleyen mesaj üretir.
    Şablon, OLAYIN DURUMUNA göre seçilir (ör. aşı: yaklaşan vs geciken farklı metin).
    Tekrar çalıştırılabilir (dedupe ile mükerrer üretmez).
    """
    from apps.appointments.models import Appointment
    from apps.vaccines.models import VaccineRecord

    today = today or timezone.localdate()
    clinic_name = ClinicSettings.load().name
    sender = (ClinicSettings.load().sender_numbers or [""])[0]
    provider = get_provider()
    created = {"appointment": 0, "vaccine": 0}

    # --- Randevu kuralları → "randevu-hatirlatma" şablonu ---
    appt_tpl = get_template("randevu-hatirlatma")
    for rule in ReminderRule.objects.filter(
        active=True, type=MessageTemplate.Type.APPOINTMENT, template__active=True
    ).select_related("template"):
        target_date = today + timedelta(days=rule.offset_days)
        template = appt_tpl or rule.template
        appts = Appointment.objects.filter(
            starts_at__date=target_date,
            reminder_enabled=True,
            status__in=[
                Appointment.Status.CONFIRMED,
                Appointment.Status.REQUESTED,
                Appointment.Status.ARRIVED,
            ],
        ).select_related("owner", "patient", "patient__species")
        for appt in appts:
            body = render_body(template.body, build_context(
                appt.owner, appt.patient, clinic_name=clinic_name,
                date=appt.starts_at.strftime("%d.%m.%Y"), time=appt.starts_at.strftime("%H:%M"),
            ))
            key = f"appt:{appt.pk}:{rule.pk}:{target_date.isoformat()}"
            if _create_message(
                owner=appt.owner, patient=appt.patient, kind=OutboundMessage.KIND_APPOINTMENT,
                body=body, scheduled_for=today, dedupe_key=key, sender=sender,
                provider=provider, appointment=appt,
            ):
                created["appointment"] += 1

    # --- Koruyucu/tedavi kuralları (aşı + iç/dış parazit + ilaç) → kategoriye göre metin ---
    # Hepsi VaccineRecord.next_due_at ile izlenir; şablon kategori + duruma göre seçilir.
    for rule in ReminderRule.objects.filter(
        active=True, type=MessageTemplate.Type.VACCINE, template__active=True
    ).select_related("template"):
        target_date = today + timedelta(days=rule.offset_days)
        # offset negatifse tarih geçmiştedir → geciken metni
        state = "geciken" if rule.offset_days < 0 else "yaklasan"
        records = VaccineRecord.objects.filter(next_due_at=target_date).select_related(
            "patient", "patient__owner", "patient__species", "vaccine_definition"
        )
        for record in records:
            prefix = CATEGORY_TEMPLATE_PREFIX.get(record.category or "vaccine", "asi")
            template = (
                get_template(f"{prefix}-{state}")
                or get_template(f"asi-{state}")
                or rule.template
            )
            body = render_body(template.body, build_context(
                record.patient.owner, record.patient, clinic_name=clinic_name,
                date=record.next_due_at.strftime("%d.%m.%Y") if record.next_due_at else "",
                vaccine=record.display_name,
            ))
            key = f"vac:{record.pk}:{rule.pk}:{target_date.isoformat()}"
            if _create_message(
                owner=record.patient.owner, patient=record.patient,
                kind=OutboundMessage.KIND_VACCINE, body=body, scheduled_for=today,
                dedupe_key=key, sender=sender, provider=provider, vaccine_record=record,
            ):
                created["vaccine"] += 1

    created["total"] = created["appointment"] + created["vaccine"]
    return created
