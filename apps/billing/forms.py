from __future__ import annotations

from django import forms

from apps.core.forms import StyledFormMixin

from .models import Charge, ChargeLine, Payment, ServiceItem


class ChargeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Charge
        fields = ["owner", "patient", "examination", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].required = False
        self.fields["examination"].required = False


class ChargeLineForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ChargeLine
        fields = ["item", "description", "qty", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].required = False
        self.fields["description"].required = False
        self.fields["qty"].required = False
        self.fields["unit_price"].required = False
        self.fields["item"].queryset = ServiceItem.objects.filter(active=True)

    def save(self, commit=True):
        from decimal import Decimal

        obj = super().save(commit=False)
        if obj.item and not obj.description:
            obj.description = obj.item.name
        if obj.item and (not obj.unit_price or obj.unit_price == 0):
            obj.unit_price = obj.item.default_price
        if not obj.qty:
            obj.qty = Decimal("1")
        if not obj.unit_price:
            obj.unit_price = Decimal("0")
        if commit:
            obj.save()
        return obj


ChargeLineFormSet = forms.inlineformset_factory(
    Charge, ChargeLine, form=ChargeLineForm, extra=4, can_delete=True
)


class PaymentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["charge", "amount", "method", "paid_at", "note"]
        widgets = {"paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, fix_charge=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paid_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        if fix_charge is not None:
            self.fields["charge"].initial = fix_charge
            self.fields["charge"].widget = forms.HiddenInput()
        else:
            # Sadece bekleyen/kısmi işlemler
            self.fields["charge"].queryset = Charge.objects.exclude(status=Charge.PAID).select_related("owner")


class ServiceItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceItem
        fields = ["name", "kind", "default_price", "active"]
