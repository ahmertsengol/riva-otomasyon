"""Form yardımcıları — tüm formlara tutarlı Tailwind stilleri uygular."""

from __future__ import annotations

from django import forms

from .models import ClinicSettings


class StyledFormMixin:
    """
    Form alanlarına widget tipine göre otomatik CSS sınıfı ekler.
    ModelForm/Form ile birlikte ilk taban olarak kullanın:
        class OwnerForm(StyledFormMixin, forms.ModelForm): ...
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput,)):
                css = "h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "select"
            elif isinstance(widget, forms.Textarea):
                css = "textarea"
                widget.attrs.setdefault("rows", 3)
            elif isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                css = ""
            else:
                css = "input"
            if css:
                widget.attrs["class"] = (existing + " " + css).strip()


class ClinicSettingsForm(StyledFormMixin, forms.ModelForm):
    sender_numbers_text = forms.CharField(
        label="Gönderen WhatsApp numaraları",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Her satıra bir numara (ör. 905059563667). Hatırlatma ekranında seçilebilir.",
    )

    class Meta:
        model = ClinicSettings
        fields = [
            "name",
            "logo",
            "phone",
            "email",
            "address",
            "weekday_hours",
            "sunday_hours",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["sender_numbers_text"].initial = "\n".join(
                self.instance.sender_numbers or []
            )

    def save(self, commit=True):
        obj = super().save(commit=False)
        raw = self.cleaned_data.get("sender_numbers_text", "")
        obj.sender_numbers = [line.strip() for line in raw.splitlines() if line.strip()]
        if commit:
            obj.save()
        return obj
