from __future__ import annotations

from django import forms
from django.utils import timezone

from apps.core.forms import StyledFormMixin

from .models import Owner


class OwnerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Owner
        fields = [
            "first_name",
            "last_name",
            "phone",
            "contact_pref",
            "tc_no",
            "email",
            "il",
            "ilce",
            "address",
            "notes",
            "kvkk_consent",
            "marketing_consent",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def save(self, commit=True):
        owner = super().save(commit=False)
        # KVKK onayı verildiyse ve tarih boşsa damgala; onay kaldırıldıysa tarihi temizle.
        if owner.kvkk_consent and not owner.kvkk_consent_at:
            owner.kvkk_consent_at = timezone.now()
        elif not owner.kvkk_consent:
            owner.kvkk_consent_at = None
        if commit:
            owner.save()
        return owner
