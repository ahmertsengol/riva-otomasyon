"""Şablonlara global olarak klinik ayarlarını ve nav rozet sayılarını sağlar."""

from __future__ import annotations


def clinic(request):
    data = {"clinic": None, "pending_request_count": 0, "due_reminder_count": 0, "action_count": 0}
    try:
        from .models import ClinicSettings

        data["clinic"] = ClinicSettings.load()
    except Exception:
        # Migrasyon öncesi / tablo yokken sessizce geç.
        return data

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        try:
            from apps.appointments.models import AppointmentRequest

            data["pending_request_count"] = AppointmentRequest.objects.filter(
                status=AppointmentRequest.NEW
            ).count()
        except Exception:
            pass
        try:
            from django.utils import timezone

            from apps.reminders.models import OutboundMessage

            # Gönderilmeyi bekleyen + zamanı gelmiş (bugün/geciken) hatırlatmalar
            data["due_reminder_count"] = OutboundMessage.objects.filter(
                status=OutboundMessage.PENDING, scheduled_for__lte=timezone.localdate()
            ).count()
        except Exception:
            pass
    # Üst bar zili: yapılması gereken toplam aksiyon
    data["action_count"] = data["due_reminder_count"] + data["pending_request_count"]
    return data
