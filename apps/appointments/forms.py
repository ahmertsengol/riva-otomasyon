from __future__ import annotations

from django import forms

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import Appointment, AppointmentRequest


class AppointmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["patient", "starts_at", "duration_min", "type", "status", "assigned_vet", "note"]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species")
        )
        self.fields["assigned_vet"].queryset = User.objects.filter(
            role__in=[User.Role.VET, User.Role.ADMIN], is_active=True
        )
        self.fields["assigned_vet"].required = False

    def save(self, commit=True):
        appt = super().save(commit=False)
        appt.owner = appt.patient.owner
        appt.phone_snapshot = appt.patient.owner.phone
        if commit:
            appt.save()
        return appt


class AppointmentRequestForm(StyledFormMixin, forms.ModelForm):
    """Elle randevu talebi ekleme (panel içi)."""

    class Meta:
        model = AppointmentRequest
        fields = ["name", "phone", "pet_name", "pet_species", "requested_at", "subject", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 2})}
