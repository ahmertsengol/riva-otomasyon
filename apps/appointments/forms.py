from __future__ import annotations

from django import forms

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin
from apps.owners.models import Owner
from apps.patients.models import Patient, Species

from .models import Appointment, AppointmentRequest


class QuickIntakeForm(StyledFormMixin, forms.Form):
    """Hızlı kabul: mevcut sahip/hayvan seç VEYA yeni oluştur; tek transaction."""

    owner = forms.ModelChoiceField(queryset=Owner.objects.all(), required=False, label="Mevcut sahip")
    new_owner_first = forms.CharField(required=False, label="Yeni sahip — Ad")
    new_owner_last = forms.CharField(required=False, label="Soyad")
    new_owner_phone = forms.CharField(required=False, label="Telefon")

    patient = forms.ModelChoiceField(queryset=Patient.objects.all(), required=False, label="Mevcut hayvan")
    new_pet_name = forms.CharField(required=False, label="Yeni hayvan — Ad")
    new_pet_species = forms.ModelChoiceField(
        queryset=Species.objects.filter(active=True), required=False, label="Tür"
    )
    new_pet_breed = forms.CharField(required=False, label="Irk")
    new_pet_sex = forms.ChoiceField(
        choices=Patient.Sex.choices, required=False, initial=Patient.Sex.UNKNOWN, label="Cinsiyet"
    )

    type = forms.ChoiceField(
        choices=Appointment.Type.choices, initial=Appointment.Type.GENERAL, label="Geliş tipi"
    )
    complaint = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Şikayet / not")
    vet = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=[User.Role.VET, User.Role.ADMIN], is_active=True),
        required=False, label="Hekim",
    )

    def clean(self):
        cleaned = super().clean()
        owner = cleaned.get("owner")
        patient = cleaned.get("patient")
        has_new_owner = bool(cleaned.get("new_owner_first") and cleaned.get("new_owner_phone"))
        has_new_pet = bool(cleaned.get("new_pet_name") and cleaned.get("new_pet_species"))

        if not owner and not has_new_owner:
            self.add_error("new_owner_first", "Mevcut sahip seçin ya da ad + telefon girin.")
        if not patient and not has_new_pet:
            self.add_error("new_pet_name", "Mevcut hayvan seçin ya da ad + tür girin.")
        if owner and patient and patient.owner_id != owner.pk:
            self.add_error("patient", "Seçilen hayvan bu sahibe ait değil.")
        return cleaned


class AppointmentForm(StyledFormMixin, forms.ModelForm):
    # Kayda yazılmayan, sadece hayvan listesini filtrelemek için sahip seçimi
    owner = forms.ModelChoiceField(
        queryset=Owner.objects.order_by("first_name", "last_name"),
        required=False,
        label="Sahip",
    )

    class Meta:
        model = Appointment
        fields = ["patient", "starts_at", "duration_min", "type", "status", "assigned_vet", "note", "reminder_enabled"]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    field_order = ["owner", "patient", "starts_at", "duration_min", "type", "status", "assigned_vet", "note", "reminder_enabled"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species")
        )
        self.fields["owner"].widget.attrs.update({
            "hx-get": "/hayvanlar/secenekler/",
            "hx-target": "#patient-field",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
        })
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
