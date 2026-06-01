from __future__ import annotations

from django import forms

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import VaccineDefinition, VaccineRecord


class VaccineDefinitionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = VaccineDefinition
        fields = [
            "name",
            "species",
            "first_dose_age_text",
            "series_doses",
            "series_interval_days",
            "repeat_interval_days",
            "reminder_offset_days",
            "description",
            "active",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class VaccineRecordForm(StyledFormMixin, forms.ModelForm):
    create_followup = forms.BooleanField(
        label="Sonraki doz için randevu oluştur",
        required=False,
        initial=True,
    )

    class Meta:
        model = VaccineRecord
        fields = [
            "patient",
            "vaccine_definition",
            "vaccine_name",
            "applied_at",
            "next_due_at",
            "vet",
            "serial_lot",
            "expiry_date",
            "note",
        ]
        widgets = {
            "applied_at": forms.DateInput(attrs={"type": "date"}),
            "next_due_at": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species").order_by("name")
        )
        # Hayvan değişince protokolleri türe göre filtrele (HTMX)
        self.fields["patient"].widget.attrs.update({
            "hx-get": "/asilar/protokol-secenekleri/",
            "hx-target": "#vaccine-def-field",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
        })
        self.fields["vaccine_definition"].queryset = VaccineDefinition.objects.filter(
            active=True
        ).select_related("species")
        self.fields["vaccine_definition"].required = False
        self.fields["vaccine_name"].required = False
        self.fields["vet"].queryset = User.objects.filter(
            role__in=[User.Role.VET, User.Role.ADMIN], is_active=True
        )
        self.fields["vet"].required = False

    def clean(self):
        cleaned = super().clean()
        definition = cleaned.get("vaccine_definition")
        vaccine_name = (cleaned.get("vaccine_name") or "").strip()
        patient = cleaned.get("patient")
        if not definition and not vaccine_name:
            self.add_error("vaccine_name", "Protokol seçilmediyse aşı adı girin.")
        if definition and patient and definition.species_id != patient.species_id:
            self.add_error("vaccine_definition", "Seçilen protokol hayvanın türüyle uyumlu değil.")
        return cleaned
