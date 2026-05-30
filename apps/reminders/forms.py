from __future__ import annotations

from django import forms

from apps.core.forms import StyledFormMixin

from .models import MessageTemplate, OutboundMessage, ReminderRule


class ManualMessageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = OutboundMessage
        fields = ["owner", "patient", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].required = False
        self.fields["patient"].label = "Hayvan"
        self.fields["owner"].queryset = self.fields["owner"].queryset.order_by(
            "first_name", "last_name"
        )
        # Sahip değişince hayvan listesini o sahibe göre filtrele (HTMX)
        self.fields["owner"].widget.attrs.update({
            "hx-get": "/hayvanlar/secenekler/",
            "hx-target": "#patient-field",
            "hx-swap": "innerHTML",
            "hx-trigger": "change",
        })


class MessageTemplateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ["name", "key", "type", "locale", "channel", "body", "active"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}


class ReminderRuleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ReminderRule
        fields = ["name", "type", "offset_days", "template", "active"]
