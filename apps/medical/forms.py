from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import (
    Examination,
    ExaminationTemplate,
    LabResult,
    Note,
    Operation,
    Prescription,
    PrescriptionItem,
)


class ExaminationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Examination
        fields = [
            "patient",
            "appointment",
            "vet",
            "template",
            "complaint",
            "anamnesis",
            "findings",
            "diagnosis",
            "treatment_plan",
            "notes",
            "follow_up_date",
        ]
        widgets = {
            "complaint": forms.Textarea(attrs={"rows": 2}),
            "anamnesis": forms.Textarea(attrs={"rows": 3}),
            "findings": forms.Textarea(attrs={"rows": 4}),
            "diagnosis": forms.Textarea(attrs={"rows": 2}),
            "treatment_plan": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species").order_by("name")
        )
        self.fields["appointment"].queryset = (
            self.fields["appointment"].queryset.select_related("patient", "owner").order_by("-starts_at")
        )
        self.fields["appointment"].required = False
        self.fields["vet"].queryset = User.objects.filter(
            role__in=[User.Role.VET, User.Role.ADMIN], is_active=True
        )
        self.fields["vet"].required = False
        self.fields["template"].queryset = ExaminationTemplate.objects.filter(active=True)
        self.fields["template"].required = False

    def clean(self):
        cleaned = super().clean()
        appointment = cleaned.get("appointment")
        patient = cleaned.get("patient")
        if appointment and patient and appointment.patient_id != patient.pk:
            self.add_error("appointment", "Randevu seçilen hayvana ait değil.")
        return cleaned


class PrescriptionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ["patient", "examination", "vet", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species").order_by("name")
        )
        self.fields["patient"].widget.attrs.update({
            "hx-get": "/muayene-secenekleri/",
            "hx-target": "#examination-field",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
        })
        self.fields["examination"].queryset = (
            self.fields["examination"]
            .queryset.select_related("patient", "vet")
            .order_by("-created_at")
        )
        self.fields["examination"].required = False
        self.fields["vet"].queryset = User.objects.filter(
            role__in=[User.Role.VET, User.Role.ADMIN], is_active=True
        )
        self.fields["vet"].required = False

    def clean(self):
        cleaned = super().clean()
        examination = cleaned.get("examination")
        patient = cleaned.get("patient")
        if examination and patient and examination.patient_id != patient.pk:
            self.add_error("examination", "Muayene seçilen hayvana ait değil.")
        return cleaned


class PrescriptionItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ["drug_name", "dose", "frequency", "duration", "note"]
        labels = {
            "drug_name": "İlaç",
            "dose": "Doz",
            "frequency": "Sıklık",
            "duration": "Süre",
            "note": "Not",
        }


PrescriptionItemFormSet = inlineformset_factory(
    Prescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=2,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class OperationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Operation
        fields = [
            "patient",
            "date",
            "vet",
            "type",
            "anesthesia_info",
            "drugs_used",
            "result",
            "notes",
            "follow_up_date",
            "post_op_instructions",
        ]
        widgets = {
            "date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "anesthesia_info": forms.Textarea(attrs={"rows": 2}),
            "drugs_used": forms.Textarea(attrs={"rows": 2}),
            "result": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "post_op_instructions": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species").order_by("name")
        )
        self.fields["vet"].queryset = User.objects.filter(
            role__in=[User.Role.VET, User.Role.ADMIN], is_active=True
        )
        self.fields["vet"].required = False


class LabResultForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ["patient", "examination", "test_name", "date", "result_note", "file"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "result_note": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species").order_by("name")
        )
        self.fields["patient"].widget.attrs.update({
            "hx-get": "/muayene-secenekleri/",
            "hx-target": "#examination-field",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
        })
        self.fields["examination"].queryset = (
            self.fields["examination"]
            .queryset.select_related("patient", "vet")
            .order_by("-created_at")
        )
        self.fields["examination"].required = False

    def clean(self):
        cleaned = super().clean()
        examination = cleaned.get("examination")
        patient = cleaned.get("patient")
        if examination and patient and examination.patient_id != patient.pk:
            self.add_error("examination", "Muayene seçilen hayvana ait değil.")
        return cleaned


class NoteForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Note
        fields = ["patient", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = (
            self.fields["patient"].queryset.select_related("owner", "species").order_by("name")
        )
