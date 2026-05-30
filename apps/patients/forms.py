from __future__ import annotations

from django import forms

from apps.core.forms import StyledFormMixin

from .models import Patient, Species


class PatientForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "owner",
            "name",
            "species",
            "breed",
            "sex",
            "birth_date",
            "age_text",
            "microchip_no",
            "neutered",
            "color",
            "weight",
            "allergies",
            "chronic_conditions",
            "notes",
            "photo",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "chronic_conditions": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sadece aktif türleri göster
        self.fields["species"].queryset = Species.objects.filter(active=True)


class SpeciesForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Species
        fields = ["name", "active"]
