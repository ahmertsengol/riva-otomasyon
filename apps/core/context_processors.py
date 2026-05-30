"""Şablonlara global olarak klinik ayarlarını ve nav rozet sayılarını sağlar."""

from __future__ import annotations


def clinic(request):
    data = {"clinic": None, "pending_request_count": 0}
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
    return data
